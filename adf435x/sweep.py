"""
Frequency-table planning and sequence playback for ADF435x synthesizers.

``FrequencyTable`` precomputes SPI write plans; ``ADF435xSweeper`` plays them
back. MicroPython-safe; no ``machine`` import.
"""

from .register_file import ADF435xRegisterFile
from .solver import (
    SolveOptions,
    _raise_divider_crossing,
    build_frequency_table,
    solve,
)
from .synthesizer import _sleep_ms


class FrequencyEntry:
    """
    One row in a frequency table.

    Parameters
    ----------
    achieved_hz : int
        Actual output frequency in hertz.
    error_hz : int
        Signed residual target minus achieved.
    plan : list of int
        Pre-encoded SPI words for this hop (R5 down to R0 order).
    fields : dict
        Register config fields; used to sync the synthesizer register file.
    """

    def __init__(self, achieved_hz, error_hz, plan, fields, divider_boundary=False):
        """Store achieved frequency, error, write plan, and config fields."""
        self.achieved_hz = achieved_hz
        self.error_hz = error_hz
        self.plan = plan
        self._fields = fields
        self.divider_boundary = divider_boundary


class FrequencyTable:
    """
    Ordered list of frequencies with pre-encoded SPI commit plans.

    Build via ``from_range`` or ``from_frequencies``; pass to ``ADF435xSweeper``.
    """

    def __init__(self, entries, channel_step_hz=0):
        """
        Store entries and optional channel-step metadata.

        Parameters
        ----------
        entries : list of FrequencyEntry
            Table rows in playback order.
        channel_step_hz : int
            RF channel spacing from MOD and fPFD (0 if not applicable).
        """
        self._entries = entries
        self._channel_step_hz = channel_step_hz

    @classmethod
    def from_range(
        cls,
        synth,
        lower_hz,
        upper_hz,
        step_hz,
        *,
        allow_divider_change=False,
    ):
        """
        Build an ascending table between *lower_hz* and *upper_hz*.

        Parameters
        ----------
        synth : ADF435xSynthesizer
            Source of profile, reference frequency, and solve options.
        lower_hz, upper_hz, step_hz : int
            Frequency bounds and desired step in hertz.
        allow_divider_change : bool
            When True, split at RF divider octaves and build an optimized
            sub-table per band (locked MOD within each segment). Divider
            boundary entries use a full register write and extended dwell
            at playback.

        Returns
        -------
        FrequencyTable

        Raises
        ------
        DividerOctaveCrossingError
            When endpoints need different RF dividers and
            *allow_divider_change* is False.
        """
        results, channel_step_hz, boundary_indices = build_frequency_table(
            lower_hz,
            upper_hz,
            step_hz,
            synth.ref_hz,
            synth.profile,
            allow_divider_change=allow_divider_change,
        )
        entries = _encode_plans(
            synth.profile,
            results,
            boundary_indices=boundary_indices,
        )
        return cls(entries, channel_step_hz)

    @classmethod
    def from_frequencies(
        cls,
        synth,
        frequencies,
        *,
        allow_divider_change=False,
    ):
        """
        Build a table from an explicit frequency list (any order).

        Parameters
        ----------
        synth : ADF435xSynthesizer
            Source of profile, reference frequency, and solve options.
        frequencies : list of int
            Target frequencies in hertz, in playback order.
        allow_divider_change : bool
            When True, group consecutive frequencies by RF divider and lock
            MOD within each group. Divider boundary entries use a full
            register write and extended dwell at playback.

        Returns
        -------
        FrequencyTable

        Raises
        ------
        ValueError
            If the list is empty.
        DividerOctaveCrossingError
            When an entry needs a different RF divider and
            *allow_divider_change* is False.
        """
        if not frequencies:
            raise ValueError("frequencies must not be empty")

        results, boundary_indices = _solve_frequencies(
            synth,
            frequencies,
            allow_divider_change=allow_divider_change,
        )
        entries = _encode_plans(
            synth.profile,
            results,
            boundary_indices=boundary_indices,
        )
        return cls(entries)

    @property
    def segment_boundaries(self):
        """Indices of divider-boundary entries (first hop in each new band)."""
        return tuple(
            i for i in range(len(self._entries))
            if self._entries[i].divider_boundary
        )

    def __len__(self):
        """Number of table entries."""
        return len(self._entries)

    def __getitem__(self, index):
        """Return the entry at *index*."""
        return self._entries[index]

    @property
    def channel_step_hz(self):
        """RF channel spacing in hertz (from range builds)."""
        return self._channel_step_hz


def _solve_frequencies(synth, frequencies, *, allow_divider_change=False):
    """
    Solve a list of target frequencies for table construction.

    Returns
    -------
    tuple of (list of SolveResult, frozenset)
        Results and indices of divider-boundary entries.
    """
    if not allow_divider_change:
        results = _solve_frequencies_locked(synth, frequencies)
        return results, frozenset()

    results = []
    boundary_indices = set()
    i = 0
    while i < len(frequencies):
        first = solve(
            frequencies[i],
            synth.ref_hz,
            synth.profile,
            options=synth._solve_options,
        )
        div = first.fields["rf_divider"]
        mod = first.fields["mod"]
        opts = SolveOptions(
            r_counter=synth._solve_options.r_counter,
            doubler=synth._solve_options.doubler,
            rdiv2=synth._solve_options.rdiv2,
            mod=mod,
        )
        if results:
            boundary_indices.add(len(results))
        results.append(first)
        i += 1
        while i < len(frequencies):
            trial = solve(
                frequencies[i],
                synth.ref_hz,
                synth.profile,
                options=opts,
            )
            if trial.fields["rf_divider"] != div:
                break
            results.append(trial)
            i += 1
    return results, frozenset(boundary_indices)


def _solve_frequencies_locked(synth, frequencies):
    """
    Solve a frequency list with MOD locked from the first entry.

    Raises ``DividerOctaveCrossingError`` when RF divider changes mid-list.
    """
    first = solve(
        frequencies[0],
        synth.ref_hz,
        synth.profile,
        options=synth._solve_options,
    )
    mod = first.fields["mod"]
    rf_divider = first.fields["rf_divider"]
    opts = SolveOptions(
        r_counter=synth._solve_options.r_counter,
        doubler=synth._solve_options.doubler,
        rdiv2=synth._solve_options.rdiv2,
        mod=mod,
    )

    results = [first]
    for hz in frequencies[1:]:
        result = solve(
            hz,
            synth.ref_hz,
            synth.profile,
            options=opts,
        )
        if result.fields["rf_divider"] != rf_divider:
            _raise_divider_crossing(
                frequencies[0],
                hz,
                rf_divider,
                result.fields["rf_divider"],
            )
        results.append(result)
    return results


def _encode_plans(profile, results, *, boundary_indices=None):
    """
    Pre-encode SPI commit plans for a list of solve results.

    Parameters
    ----------
    boundary_indices : frozenset of int or None
        Table indices that start a new RF divider band (full R5..R0 write).
    """
    boundary_indices = (
        boundary_indices if boundary_indices is not None else frozenset()
    )
    regfile = ADF435xRegisterFile(profile)
    entries = []
    prev_divider = None
    for i, result in enumerate(results):
        regfile.configure(**result.fields)
        div = result.fields["rf_divider"]
        is_boundary = i in boundary_indices or (
            prev_divider is not None and div != prev_divider
        )
        if i == 0 or is_boundary:
            plan = regfile.commit_all_plan()
        else:
            plan = regfile.commit_plan()
        entries.append(
            FrequencyEntry(
                result.achieved_hz,
                result.error_hz,
                plan,
                result.fields,
                divider_boundary=is_boundary,
            )
        )
        regfile.mark_written()
        prev_divider = div
    return entries


class ADF435xSweeper:
    """
    Play back a ``FrequencyTable`` through a synthesizer.

    Parameters
    ----------
    synth : ADF435xSynthesizer
        Target synthesizer (duck-typed device inside).
    table : FrequencyTable
        Precomputed frequency sequence.
    dwell_ms : int
        Milliseconds to wait after each hop (default 0).
    wait_for_lock : bool
        When True, call ``wait_locked()`` after each in-band hop.
    boundary_dwell_ms : int
        Milliseconds to dwell after a divider-boundary hop (default 500).
        Boundary hops always wait for lock regardless of *wait_for_lock*.
    """

    def __init__(
        self,
        synth,
        table,
        *,
        dwell_ms=0,
        wait_for_lock=False,
        boundary_dwell_ms=500,
    ):
        """Store synthesizer, table, and playback options."""
        self._synth = synth
        self._table = table
        self._dwell_ms = dwell_ms
        self._wait_for_lock = wait_for_lock
        self._boundary_dwell_ms = boundary_dwell_ms
        self._ready = False
        self._index = 0

    @classmethod
    def run_range(
        cls,
        synth,
        lower_hz,
        upper_hz,
        step_hz,
        *,
        dwell_ms=0,
        wait_for_lock=False,
        allow_divider_change=False,
        boundary_dwell_ms=500,
    ):
        """
        Build a range table, play once, and return.

        Parameters
        ----------
        synth : ADF435xSynthesizer
        lower_hz, upper_hz, step_hz : int
        dwell_ms : int
        wait_for_lock : bool
        allow_divider_change : bool
            Passed to ``FrequencyTable.from_range``.
        boundary_dwell_ms : int
            Dwell after divider-boundary hops.
        """
        table = FrequencyTable.from_range(
            synth,
            lower_hz,
            upper_hz,
            step_hz,
            allow_divider_change=allow_divider_change,
        )
        player = cls(
            synth,
            table,
            dwell_ms=dwell_ms,
            wait_for_lock=wait_for_lock,
            boundary_dwell_ms=boundary_dwell_ms,
        )
        player.run()

    @property
    def index(self):
        """Current playback index (entries already written)."""
        return self._index

    def reset(self):
        """Reset playback index and ready state."""
        self._ready = False
        self._index = 0

    def run(self, *, cycles=1):
        """
        Play the table cyclically.

        Parameters
        ----------
        cycles : int
            Number of times to play the full table.
        """
        for cycle in range(cycles):
            if cycle > 0:
                self._index = 0
            while self.step() is not None:
                pass

    def step(self):
        """
        Advance one table entry.

        Returns
        -------
        int or None
            Achieved frequency in hertz, or None when the table is exhausted.
        """
        self._ensure_ready()
        if self._index >= len(self._table):
            return None
        entry = self._table[self._index]
        self._play_entry(entry)
        self._index += 1
        return entry.achieved_hz

    def _ensure_ready(self):
        """Enable fast-hop register settings and chip power."""
        if self._ready:
            return
        self._synth._enable_fast_hop_mode()
        if not self._synth.is_powered:
            self._synth._device.chip_enable()
            self._synth._powered = True
        self._ready = True

    def _play_entry(self, entry):
        """
        Write one table entry and optionally wait.

        Parameters
        ----------
        entry : FrequencyEntry
        """
        self._synth._regfile.configure(**entry._fields)
        self._synth._achieved_hz = entry.achieved_hz
        self._synth._target_hz = entry.achieved_hz + entry.error_hz
        self._synth._write_prebuilt_plan(entry.plan)
        if entry.divider_boundary:
            self._synth.wait_locked()
            if self._boundary_dwell_ms > 0:
                _sleep_ms(self._boundary_dwell_ms)
        else:
            if self._wait_for_lock:
                self._synth.wait_locked()
            if self._dwell_ms > 0:
                _sleep_ms(self._dwell_ms)

