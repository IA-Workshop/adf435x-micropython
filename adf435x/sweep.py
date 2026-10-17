"""
Frequency tables for fast hopping and sweeps on ADF435x synthesizers.

``FrequencyTable.from_range`` and ``FrequencyTable.from_frequencies`` solve
every point once, at setup, and store each entry's register fields together
with all six encoded words. Play a table with ``ADF435xSynthesizer.play()``
(or one entry at a time with ``play_step()``); each hop writes only the
registers that differ from what was last written to the chip.

Words are encoded from a copy of the synthesizer's own settings (output
power, charge-pump current, MUXOUT, ...) with double buffering enabled for
fast hops. If those settings change after the table is built, the next hop
re-encodes the words from the new settings first.

MOD rule
--------
Within each RF-divider band, the table looks for one MOD that hits every
point exactly (the least common multiple of each point's MOD). If that MOD
fits the device (<= 4095), all entries share it and in-band hops are a
single R0 write. Otherwise each point gets its own best MOD, and a hop
whose MOD differs from the previous one also writes R1. Accuracy is never
traded away silently: see ``max_error_hz``.

MicroPython-safe; no ``machine`` import.
"""

from .register_file import ADF435xRegisterFile
from .solver import max_hz_for_rf_divider, output_band_hz, pll_mode_fields

# Fields every table entry sets on top of the synthesizer's settings: R4's RF
# divider latches on R0 (data sheet p.12) so a divider change takes effect
# together with the new N.
_FAST_HOP_FIELDS = {"double_buffer": True}


class DividerOctaveCrossingError(ValueError):
    """
    A frequency table needs more than one RF output divider.

    Raised when ``allow_divider_change`` is False.

    Attributes
    ----------
    lower_hz, upper_hz : int
        The lower and higher of the two frequencies that need different
        dividers.
    lower_divider, upper_divider : int
        The RF dividers those frequencies need.
    lower_band_hz, upper_band_hz : tuple of (int, int)
        The frequency range each of those dividers covers, as chosen by the
        solver (``(min_hz, max_hz)``).
    """

    def __init__(self, lower_hz, upper_hz, lower_divider, upper_divider, profile):
        """Build the message with ranges that stay on one divider."""
        self.lower_hz = lower_hz
        self.upper_hz = upper_hz
        self.lower_divider = lower_divider
        self.upper_divider = upper_divider
        self.lower_band_hz = _divider_band(lower_divider, profile)
        self.upper_band_hz = _divider_band(upper_divider, profile)
        super().__init__(
            "RF divider octave crossing: %d Hz uses divide-by-%d "
            "(band %d-%d Hz), %d Hz needs divide-by-%d (band %d-%d Hz). "
            "Narrow to [%d, %d] or [%d, %d], or set allow_divider_change=True."
            % (
                lower_hz,
                lower_divider,
                self.lower_band_hz[0],
                self.lower_band_hz[1],
                upper_hz,
                upper_divider,
                self.upper_band_hz[0],
                self.upper_band_hz[1],
                lower_hz,
                min(upper_hz, self.lower_band_hz[1]),
                max(lower_hz, self.upper_band_hz[0]),
                upper_hz,
            )
        )


def _divider_band(rf_divider, profile):
    """Frequencies for which the solver picks *rf_divider*: ``(lo, hi)``."""
    low = output_band_hz(rf_divider)[0]
    return low, max_hz_for_rf_divider(rf_divider, profile)


class FrequencyEntry:
    """
    One row of a frequency table.

    Attributes
    ----------
    target_hz : int
        Requested frequency.
    achieved_hz : int
        Output frequency, rounded to the nearest hertz.
    error_hz : int
        ``target_hz - achieved_hz``.
    exact : bool
        True when the output is exactly the target.
    fields : dict
        Register fields this entry sets (solver fields plus fast-hop
        settings).
    words : list of int
        All six register words, R0..R5, for the table's settings.
    divider_boundary : bool
        True when this entry's RF divider differs from the previous entry's.
    """

    def __init__(self, result, fields, divider_boundary):
        """Store one solved, encoded table row."""
        self.target_hz = result.achieved_hz + result.error_hz
        self.achieved_hz = result.achieved_hz
        self.error_hz = result.error_hz
        self.exact = result.exact
        self.fields = fields
        self.words = None
        self.divider_boundary = divider_boundary
        self._pfd = result.f_pfd_fraction

    @property
    def rf_divider(self):
        """RF output divider of this entry."""
        return self.fields["rf_divider"]


class FrequencyTable:
    """
    Ordered, pre-solved frequencies for ``ADF435xSynthesizer.play()``.

    Build with ``from_range`` or ``from_frequencies``; index it like a list.
    """

    def __init__(self, entries, profile, regfile):
        """Store entries and encode their words from *regfile*'s settings."""
        self._entries = entries
        self._version = None
        self._profile = profile
        self.sync(regfile)

    @classmethod
    def from_range(
        cls,
        synth,
        lower_hz,
        upper_hz,
        step_hz,
        *,
        allow_divider_change=False,
        max_error_hz=None,
    ):
        """
        Build an ascending table ``lower_hz, lower_hz + step_hz, ...``.

        The last entry is ``upper_hz`` (added if the steps do not land on it).

        Parameters
        ----------
        synth : ADF435xSynthesizer
            Supplies the profile, reference path, and register settings.
        lower_hz, upper_hz, step_hz : int
            Bounds and step in hertz; ``lower_hz <= upper_hz``, ``step_hz > 0``.
        allow_divider_change : bool
            Allow the range to span several RF dividers. Entries that start a
            new divider are marked ``divider_boundary``.
        max_error_hz : int or None
            Raise ``ValueError`` if any entry's error exceeds this.

        Raises
        ------
        DividerOctaveCrossingError
            If the range needs several RF dividers and *allow_divider_change*
            is False.
        ValueError
            On invalid bounds or step, or if *max_error_hz* is exceeded.
        """
        for name, value in (
            ("lower_hz", lower_hz),
            ("upper_hz", upper_hz),
            ("step_hz", step_hz),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError("%s must be an integer number of hertz" % name)
        if lower_hz > upper_hz:
            raise ValueError("lower_hz must not exceed upper_hz")
        if step_hz <= 0:
            raise ValueError("step_hz must be positive")
        targets = list(range(lower_hz, upper_hz + 1, step_hz))
        if targets[-1] != upper_hz:
            targets.append(upper_hz)
        return cls._build(synth, targets, allow_divider_change, max_error_hz)

    @classmethod
    def from_frequencies(
        cls,
        synth,
        frequencies,
        *,
        allow_divider_change=False,
        max_error_hz=None,
    ):
        """
        Build a table from an explicit list, kept in the given order.

        Parameters
        ----------
        synth : ADF435xSynthesizer
            Supplies the profile, reference path, and register settings.
        frequencies : list of int
            Target frequencies in hertz, in playback order.
        allow_divider_change : bool
            Allow entries on different RF dividers.
        max_error_hz : int or None
            Raise ``ValueError`` if any entry's error exceeds this.

        Raises
        ------
        ValueError
            If the list is empty, or *max_error_hz* is exceeded.
        DividerOctaveCrossingError
            If entries need different RF dividers and *allow_divider_change*
            is False.
        """
        if not frequencies:
            raise ValueError("frequencies must not be empty")
        return cls._build(synth, list(frequencies), allow_divider_change, max_error_hz)

    @classmethod
    def _build(cls, synth, targets, allow_divider_change, max_error_hz):
        """Solve, group by divider, apply the MOD rule, and encode."""
        results = [synth.solve(hz) for hz in targets]
        if not allow_divider_change:
            first = results[0].fields["rf_divider"]
            for hz, result in zip(targets, results):
                if result.fields["rf_divider"] != first:
                    pair = sorted(((targets[0], first), (hz, result.fields["rf_divider"])))
                    raise DividerOctaveCrossingError(
                        pair[0][0], pair[1][0], pair[0][1], pair[1][1], synth.profile
                    )
        entries = []
        start = 0
        while start < len(results):
            divider = results[start].fields["rf_divider"]
            end = start
            while end < len(results) and results[end].fields["rf_divider"] == divider:
                end += 1
            segment = _lock_segment(synth, targets[start:end], results[start:end])
            for offset, (result, fields) in enumerate(segment):
                boundary = bool(entries) and offset == 0
                entries.append(FrequencyEntry(result, fields, boundary))
            start = end
        table = cls(entries, synth.profile, synth.regfile)
        if max_error_hz is not None and table.max_error_hz > max_error_hz:
            raise ValueError(
                "table error %d Hz exceeds max_error_hz=%d"
                % (table.max_error_hz, max_error_hz)
            )
        return table

    def sync(self, regfile):
        """
        Re-encode every entry's words if *regfile*'s settings changed.

        Called by ``ADF435xSynthesizer.play_step()`` before each hop; cheap
        when nothing changed (one integer comparison).
        """
        if regfile.config_version == self._version:
            return
        encoder = ADF435xRegisterFile(self._profile, config=regfile.config.copy())
        for entry in self._entries:
            encoder.configure(**entry.fields)
            entry.words = encoder.current_words()
        self._version = regfile.config_version

    def __len__(self):
        """Number of entries."""
        return len(self._entries)

    def __getitem__(self, index):
        """Return the entry at *index*."""
        return self._entries[index]

    @property
    def max_error_hz(self):
        """Largest ``abs(error_hz)`` over all entries."""
        return max(abs(entry.error_hz) for entry in self._entries)

    @property
    def channel_step_hz(self):
        """
        RF channel spacing in hertz when all entries share one divider and
        MOD (and it is a whole number of hertz); otherwise 0.
        """
        mods = {entry.fields["mod"] for entry in self._entries}
        dividers = {entry.rf_divider for entry in self._entries}
        if len(mods) != 1 or len(dividers) != 1:
            return 0
        entry = self._entries[0]
        pfd_num, pfd_den = entry._pfd
        den = pfd_den * entry.fields["mod"] * entry.rf_divider
        return pfd_num // den if pfd_num % den == 0 else 0


def _gcd(a, b):
    """Greatest common divisor (MicroPython's ``math`` has no ``gcd``)."""
    while b:
        a, b = b, a % b
    return a


def _reduced_mod(fields):
    """MOD of an entry's N in lowest terms."""
    return fields["mod"] // _gcd(fields["frac"], fields["mod"])


def _lock_segment(synth, targets, results):
    """
    Apply the MOD rule to one RF-divider segment.

    Returns
    -------
    list of (SolveResult, dict)
        Each entry's result and the fields to store for it.
    """
    profile = synth.profile
    locked = None
    if all(result.exact for result in results):
        lcm = 1
        for result in results:
            q = _reduced_mod(result.fields)
            lcm = lcm * q // _gcd(lcm, q)
            if lcm > profile.mod_max:
                break
        mod_min = synth.mod_min
        if lcm < mod_min:
            lcm *= (mod_min + lcm - 1) // lcm
        if lcm <= profile.mod_max:
            locked = lcm
    if locked is not None:
        divider = results[0].fields["rf_divider"]
        options = synth.solve_options.copy(mod=locked, rf_divider=divider)
        results = [synth.solve(hz, options=options) for hz in targets]
        # One lock-detect / ABP / charge-cancel mode for the whole segment,
        # so a channel that lands on FRAC = 0 does not rewrite R2 and R3.
        integer_n = all(result.fields["frac"] == 0 for result in results)
        mode = pll_mode_fields(integer_n, profile)
    out = []
    for result in results:
        fields = dict(result.fields)
        if locked is not None:
            fields.update(mode)
        fields.update(_FAST_HOP_FIELDS)
        out.append((result, fields))
    return out
