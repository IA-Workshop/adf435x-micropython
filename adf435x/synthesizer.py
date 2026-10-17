"""Drive an ADF4350 or ADF4351 by output frequency, in hertz.

``ADF435xSynthesizer`` solves the PLL settings, keeps the register file, and
writes only the registers that changed. It does not import ``machine``: give
it any device object with ``write_registers()``, ``chip_enable()``,
``chip_disable()`` and ``read_muxout()``. See docs/api-guide.md.
"""

import time

from . import consts
from .profiles import ADF435xDeviceProfile
from .register_file import ADF435xRegisterFile
from .solver import (
    LOW_SPUR_MOD_MIN,
    SolveOptions,
    SolveResult,
    reference_fields,
    solve,
)

# Extra wait before the first lock-detect poll, on top of band select and the
# lock-detect cycle count. Provisional: not yet measured on hardware.
LOCK_SETTLE_MARGIN_US = 10

# Microsecond clock: MicroPython's ticks (which wrap), or time.monotonic().
if hasattr(time, "ticks_us"):
    _ticks_us = time.ticks_us
    _ticks_diff = time.ticks_diff
    _ticks_add = time.ticks_add
    _sleep_us = time.sleep_us
else:

    def _ticks_us():
        """Return a timestamp in microseconds."""
        return int(time.monotonic() * 1_000_000)

    def _ticks_diff(a, b):
        """Return ``a - b`` for two timestamps."""
        return a - b

    def _ticks_add(a, b):
        """Return timestamp *a* plus *b* microseconds."""
        return a + b

    def _sleep_us(us):
        """Sleep for *us* microseconds."""
        time.sleep(us / 1_000_000)


class LockTimeoutError(RuntimeError):
    """Lock detect did not go high in time while playing a table."""


class ADF435xSynthesizer:
    """
    Drive one ADF4350 or ADF4351 by output frequency.

    Parameters
    ----------
    device
        Usually an ``ADF435xDevice``. Its ``read_muxout()`` may raise
        ``RuntimeError`` if MUXOUT is not wired; lock detect is then off.
    profile : ADF435xDeviceProfile
        ``ADF4350`` or ``ADF4351``.
    ref_hz : int
        Reference frequency (REFIN), in whole hertz.
    r_counter : int, optional
        Reference divider R (default 1).
    doubler : bool, optional
        Turn on the reference doubler (default False).
    rdiv2 : bool, optional
        Turn on the reference divide-by-2 (default False).
    """

    def __init__(
        self,
        device,
        profile,
        ref_hz,
        *,
        r_counter=1,
        doubler=False,
        rdiv2=False,
    ):
        """Build the register file and set the reference path in it."""
        self._device = device
        self._profile = profile
        self._ref_hz = ref_hz
        self._solve_options = SolveOptions(
            r_counter=r_counter,
            doubler=doubler,
            rdiv2=rdiv2,
        )
        self._regfile = ADF435xRegisterFile(profile)

        # The reference path does not depend on the frequency. Set it now so
        # no write ever carries the placeholder R and band-select values.
        reference = reference_fields(ref_hz, profile, self._solve_options)
        self._regfile.configure(**reference)

        self._powered = False
        self._target_hz = None
        self._achieved_hz = None
        self._last_write_us = None
        self._has_lock_detect = None

    @property
    def profile(self):
        """The part: ``ADF4350`` or ``ADF4351``."""
        return self._profile

    @property
    def ref_hz(self):
        """Reference frequency in hertz."""
        return self._ref_hz

    @property
    def regfile(self):
        """The ``ADF435xRegisterFile``, for setting fields directly."""
        return self._regfile

    @property
    def frequency(self):
        """The last target frequency in hertz, or None."""
        return self._target_hz

    @property
    def achieved_hz(self):
        """The last achieved output frequency in hertz, or None."""
        return self._achieved_hz

    @property
    def is_powered(self):
        """True while CE is high."""
        return self._powered

    @property
    def solve_options(self):
        """The ``SolveOptions`` used for every solve."""
        return self._solve_options

    @property
    def mod_min(self):
        """The smallest MOD the current settings allow (50 in low-spur mode)."""
        floor = self._profile.mod_min
        if self._solve_options.mod_min:
            floor = max(floor, self._solve_options.mod_min)
        if self._regfile.config.noise_mode == consts.REG2_LOW_SPUR:
            floor = max(floor, LOW_SPUR_MOD_MIN)
        return floor

    @property
    def has_lock_detect(self):
        """True if the device can read MUXOUT. Checked once, then remembered."""
        if self._has_lock_detect is None:
            try:
                self._device.read_muxout()
                self._has_lock_detect = True
            except RuntimeError:
                self._has_lock_detect = False
        return self._has_lock_detect

    @property
    def last_write_us(self):
        """Timestamp, in microseconds, of the last successful write, or None."""
        return self._last_write_us

    def power_up(self, *, frequency_hz=None):
        """Raise CE and write all six registers, R5 first.

        *frequency_hz* is needed unless a frequency is already set, for
        example by ``set_frequency()`` while powered down. It is solved
        before CE goes high, so if it is missing or cannot be solved the call
        raises (``ValueError``, or ``TypeError`` for a float) and the chip
        stays off.
        """
        if frequency_hz is not None:
            self._apply_solve(frequency_hz)
        elif self._target_hz is None:
            raise ValueError("power_up() needs frequency_hz until a frequency is set")
        self._device.chip_enable()
        self._powered = True
        self._write_stale_registers(all_registers=True)

    def power_down(self):
        """Drive CE low. The chip keeps its register contents."""
        self._device.chip_disable()
        self._powered = False

    def set_frequency(self, hz):
        """Tune to *hz* and return the ``SolveResult``.

        When powered up, the changed registers are written at once. When
        powered down, the settings are only stored, and ``power_up()``
        writes them.
        """
        result = self._apply_solve(hz)
        if self._powered:
            self._write_stale_registers()
        return result

    def is_locked(self):
        """Read MUXOUT once; True means locked.

        Raises ``RuntimeError`` if MUXOUT is not wired or is not set to
        digital lock detect.
        """
        if self._regfile.config.muxout != consts.REG2_MUX_DIGITALLOCK:
            raise RuntimeError("MUXOUT is not routed to digital lock detect")
        return bool(self._device.read_muxout())

    def wait_locked(self, timeout_us=100_000):
        """Poll lock detect for up to *timeout_us*; return True once locked.

        Right after a write it first waits ``lock_settle_us()``, so a
        "locked" reading left over from the previous frequency is not
        mistaken for lock at the new one.
        """
        if self._last_write_us is not None:
            settle = self.lock_settle_us()
            remaining = settle - _ticks_diff(_ticks_us(), self._last_write_us)
            if remaining > 0:
                _sleep_us(remaining)
        deadline = _ticks_add(_ticks_us(), timeout_us)
        while _ticks_diff(deadline, _ticks_us()) > 0:
            if self.is_locked():
                return True
            _sleep_us(100)
        return self.is_locked()

    def lock_settle_us(self):
        """Return the microseconds from a write until lock detect is reliable.

        Band select takes 10 band-select clock cycles (data sheet p.12), then
        lock detect needs 40 (fractional-N) or 5 (integer-N) PFD cycles
        (p.19). ``LOCK_SETTLE_MARGIN_US`` is added on top.
        """
        c = self._regfile.config
        pfd_num = self._ref_hz * (2 if c.doubler else 1)
        pfd_den = c.r_counter * (2 if c.rdiv2 else 1)
        lock_cycles = 5 if c.ldf == consts.REG2_LDF_INT_N else 40
        cycles = 10 * c.band_clk_div + lock_cycles

        # Round the cycle time up to a whole microsecond.
        settle = (cycles * pfd_den * 1_000_000 + pfd_num - 1) // pfd_num
        return settle + LOCK_SETTLE_MARGIN_US

    def mute(self):
        """Turn the RF output off. The PLL keeps running."""
        self._regfile.configure(rf_enable=False)
        if self._powered:
            self._write_stale_registers()

    def unmute(self):
        """Turn the RF output back on."""
        self._regfile.configure(rf_enable=True)
        if self._powered:
            self._write_stale_registers()

    def set_output_power(self, code):
        """Set the output power to one of the ``consts.REG4_POWER_*`` codes."""
        self._regfile.configure(output_power=code)
        if self._powered:
            self._write_stale_registers()

    def solve(self, hz, *, options=None):
        """Return the ``SolveResult`` for *hz* without changing anything.

        Uses this synthesizer's ``solve_options`` unless *options* is given.
        In low-spur noise mode it asks for MOD >= 50, that mode's minimum
        (data sheet p.23).
        """
        opts = options or self._solve_options
        if self.mod_min > (opts.mod_min or 0):
            opts = opts.copy(mod_min=self.mod_min)
        return solve(hz, self._ref_hz, self._profile, options=opts)

    def _apply_solve(self, hz):
        """Solve *hz*, store the fields in the register file, return the result."""
        result = self.solve(hz)
        self._regfile.configure(**result.fields)
        self._target_hz = hz
        self._achieved_hz = result.achieved_hz
        return result

    # -- frequency-table playback --------------------------------------------

    def play_step(self, table, index):
        """Program entry *index* of *table* and return that ``FrequencyEntry``.

        Only the registers that differ from the last write are sent, so the
        hop is right whatever came before it. Raises CE first if the chip is
        powered down.
        """
        table.sync(self._regfile)
        entry = table[index]
        if not self._powered:
            self._device.chip_enable()
            self._powered = True
        self._regfile.load_prevalidated(entry.fields, entry.words)
        self._target_hz = entry.target_hz
        self._achieved_hz = entry.achieved_hz
        self._write_stale_registers()
        return entry

    def play(
        self,
        table,
        *,
        dwell_us=0,
        wait_for_lock=False,
        boundary_dwell_us=500_000,
        require_lock=False,
        cycles=1,
    ):
        """
        Play *table* from the start, *cycles* times.

        Returns the number of lock waits that timed out. See docs/sweeps.md.

        Parameters
        ----------
        dwell_us : int
            Microseconds to wait after each in-band hop.
        wait_for_lock : bool
            Wait for lock detect after each in-band hop.
        boundary_dwell_us : int
            Microseconds to wait after a hop that changes the RF divider.
            These hops also wait for lock detect if MUXOUT is wired.
        require_lock : bool
            Raise ``LockTimeoutError`` instead of counting a timeout.
        cycles : int
            Number of passes through the table.
        """
        timeouts = 0
        for _ in range(cycles):
            for index in range(len(table)):
                divider_before = self._regfile.config.rf_divider
                entry = self.play_step(table, index)
                boundary = entry.rf_divider != divider_before

                if (boundary or wait_for_lock) and self.has_lock_detect:
                    if not self.wait_locked():
                        timeouts += 1
                        if require_lock:
                            raise LockTimeoutError(
                                "no lock at %d Hz (entry %d)"
                                % (entry.achieved_hz, index)
                            )

                pause = boundary_dwell_us if boundary else dwell_us
                if pause > 0:
                    _sleep_us(pause)
        return timeouts

    def _write_stale_registers(self, *, all_registers=False):
        """Write the stale registers, or all six if *all_registers* is True."""
        if all_registers:
            plan = self._regfile.commit_all_plan()
        else:
            plan = self._regfile.commit_plan()
        if plan:
            self._write_prebuilt_plan(plan)

    def _write_prebuilt_plan(self, words):
        """Write *words* (R5 first), then record success or failure."""
        try:
            self._device.write_registers(words)
            self._regfile.mark_written()
            self._last_write_us = _ticks_us()
        except Exception:
            self._regfile.mark_write_failed()
            raise
