"""Frequency tables: solve a list of frequencies once, then hop through them.

Each entry stores its register fields and all six encoded words, built from
the synthesizer's own settings, so a hop only writes the registers that
differ from the last write. The MOD rule: within each RF divider band, if
one MOD of 4095 or less hits every point exactly (the least common multiple
of their MODs), every entry uses it and an in-band hop is a single R0
write. Otherwise each point gets its own best MOD, and a hop to a different
MOD also writes R1. See docs/sweeps.md.
"""

from .register_file import ADF435xRegisterFile
from .solver import max_hz_for_rf_divider, output_band_hz, pll_mode_fields

# Set on every entry. With double buffering on, a new RF divider waits for
# the R0 write (data sheet p.12), so it takes effect together with the new N.
_FAST_HOP_FIELDS = {"double_buffer": True}


class DividerOctaveCrossingError(ValueError):
    """
    A table needs more than one RF divider, and ``allow_divider_change`` is off.

    The message suggests ranges that stay on one divider.

    Attributes
    ----------
    lower_hz, upper_hz : int
        The two frequencies that need different dividers, lower first.
    lower_divider, upper_divider : int
        The RF divider each one needs.
    lower_band_hz, upper_band_hz : tuple of (int, int)
        ``(min_hz, max_hz)``: the range over which the solver uses each of
        those dividers.
    """

    def __init__(self, lower_hz, upper_hz, lower_divider, upper_divider, profile):
        """Store the details and build the message."""
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
    """Return ``(lo, hi)``, the range over which the solver picks *rf_divider*."""
    low = output_band_hz(rf_divider)[0]
    return low, max_hz_for_rf_divider(rf_divider, profile)


class FrequencyEntry:
    """
    One row of a frequency table.

    Attributes
    ----------
    target_hz : int
        The frequency asked for.
    achieved_hz : int
        Output frequency, rounded to the nearest hertz.
    error_hz : int
        ``target_hz - achieved_hz``.
    exact : bool
        True when the output is exactly the target.
    fields : dict
        Register fields this entry sets: the solver's, plus double buffering.
    words : list of int
        All six register words, R0 first.
    divider_boundary : bool
        True when this entry's RF divider differs from the previous entry's.
    """

    def __init__(self, result, fields, divider_boundary):
        """Store one solved row. ``FrequencyTable`` fills in ``words``."""
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
        """This entry's RF divider."""
        return self.fields["rf_divider"]


class FrequencyTable:
    """
    Frequencies solved ahead of time, for ``ADF435xSynthesizer.play()``.

    Build one with ``from_range()`` or ``from_frequencies()``, then index it
    like a list. A table belongs to the synthesizer it was built with.
    """

    def __init__(self, entries, profile, regfile):
        """Store *entries* and encode their words from *regfile*'s settings."""
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
        Build a table of ``lower_hz, lower_hz + step_hz, ...`` up to ``upper_hz``.

        ``upper_hz`` is always the last entry, even if the steps miss it.

        Parameters
        ----------
        synth : ADF435xSynthesizer
            Supplies the part, the reference path and the register settings.
        lower_hz, upper_hz, step_hz : int
            Whole hertz, with ``lower_hz <= upper_hz`` and ``step_hz > 0``.
        allow_divider_change : bool
            Allow more than one RF divider. Each entry that starts a new
            divider has ``divider_boundary`` set.
        max_error_hz : int or None
            Raise ``ValueError`` if any entry is further than this from its
            target.

        Raises
        ------
        TypeError
            A bound or the step is not an integer.
        DividerOctaveCrossingError
            The range needs several RF dividers and *allow_divider_change*
            is False.
        ValueError
            Bad bounds or step, or *max_error_hz* exceeded.
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
        Build a table from a list of frequencies, kept in the order given.

        *frequencies* must not be empty. The other arguments and errors are
        as for ``from_range()``.
        """
        if not frequencies:
            raise ValueError("frequencies must not be empty")
        return cls._build(synth, list(frequencies), allow_divider_change, max_error_hz)

    @classmethod
    def _build(cls, synth, targets, allow_divider_change, max_error_hz):
        """Solve every target, group by divider, apply the MOD rule, encode."""
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
        """Re-encode every entry's words if *regfile*'s settings have changed.

        ``ADF435xSynthesizer.play_step()`` calls this before each hop. When
        nothing changed it costs one integer comparison.
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
        """The largest ``abs(error_hz)`` of any entry."""
        return max(abs(entry.error_hz) for entry in self._entries)

    @property
    def channel_step_hz(self):
        """Channel spacing at the RF output, in hertz, or 0.

        It is 0 unless every entry shares one divider and one MOD and the
        spacing is a whole number of hertz.
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
    """Return the greatest common divisor. MicroPython's ``math`` has no gcd."""
    while b:
        a, b = b, a % b
    return a


def _reduced_mod(fields):
    """Return the MOD of an entry's N = INT + FRAC/MOD in lowest terms."""
    return fields["mod"] // _gcd(fields["frac"], fields["mod"])


def _lock_segment(synth, targets, results):
    """Apply the MOD rule to targets that share one RF divider.

    Returns a list of ``(SolveResult, fields)`` pairs, one per target.
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
        # One PLL mode for the whole segment, so a channel that lands on
        # FRAC = 0 does not rewrite R2 and R3.
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
