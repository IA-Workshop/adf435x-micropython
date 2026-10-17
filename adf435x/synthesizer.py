"""
Frequency-first facade for ADF435x PLL synthesizers.

Owns the register file, frequency solver, and SPI write path (plan/mark split).
Does not import ``machine``; pass a duck-typed device with ``write_registers``,
``chip_enable``, ``chip_disable``, and ``read_muxout``.
"""

import time

from . import consts
from .profiles import ADF435xDeviceProfile
from .register_file import ADF435xRegisterFile
from .solver import LOW_SPUR_MOD_MIN, SolveOptions, SolveResult, solve

_TICKS_US_STUB = 0


def _ticks_us():
    """
    Return a microsecond timestamp.

    Uses ``time.ticks_us()`` on MicroPython; ``time.monotonic()`` under CPython.
    """
    try:
        return time.ticks_us()
    except AttributeError:
        return int(time.monotonic() * 1_000_000)


class ADF435xSynthesizer:
    """
    Set output frequency in hertz; the library solves PLL fields and writes SPI.

    Parameters
    ----------
    device
        Object with ``write_registers``, ``chip_enable``, ``chip_disable``,
        and ``read_muxout`` (MUXOUT optional for lock detect).
    profile : ADF435xDeviceProfile
        ADF4350 or ADF4351 capability profile.
    ref_hz : int
        Reference input frequency in hertz (integer only).
    r_counter : int, optional
        R-counter divide ratio (default 1).
    doubler : bool, optional
        Enable reference doubler (default False).
    rdiv2 : bool, optional
        Enable reference divide-by-two (default False).
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
        """Store device, profile, reference frequency, and build register file."""
        self._device = device
        self._profile = profile
        self._ref_hz = ref_hz
        self._solve_options = SolveOptions(
            r_counter=r_counter,
            doubler=doubler,
            rdiv2=rdiv2,
        )
        self._regfile = ADF435xRegisterFile(profile)
        self._powered = False
        self._target_hz = None
        self._achieved_hz = None
        self._last_write_us = None
        self._fast_hop_mode = False

    @property
    def profile(self):
        """Device profile (ADF4350 or ADF4351)."""
        return self._profile

    @property
    def ref_hz(self):
        """Reference input frequency in hertz."""
        return self._ref_hz

    @property
    def regfile(self):
        """Register file for advanced configuration."""
        return self._regfile

    @property
    def frequency(self):
        """Last target frequency in hertz, or None if never set."""
        return self._target_hz

    @property
    def achieved_hz(self):
        """Last achieved output frequency in hertz, or None if never set."""
        return self._achieved_hz

    @property
    def is_powered(self):
        """True if chip enable has been driven high."""
        return self._powered

    @property
    def last_write_us(self):
        """Microsecond timestamp of the last successful SPI write, or None."""
        return self._last_write_us

    def power_up(self, *, frequency_hz=None):
        """
        Enable the chip and write all registers.

        Parameters
        ----------
        frequency_hz : int or None
            Optional initial output frequency. When set, PLL fields are
            solved before the full R5..R0 write.
        """
        self._device.chip_enable()
        self._powered = True
        if frequency_hz is not None:
            self._apply_solve(frequency_hz)
        self._write_stale_registers(all_registers=True)

    def power_down(self):
        """Drive chip enable low."""
        self._device.chip_disable()
        self._powered = False

    def set_frequency(self, hz):
        """
        Solve and write a new output frequency.

        Parameters
        ----------
        hz : int
            Target output frequency in hertz.

        Returns
        -------
        SolveResult
            Achieved frequency, error, and field dict from the solver.
        """
        result = self._apply_solve(hz)
        self._write_stale_registers()
        return result

    def is_locked(self):
        """
        Read digital lock detect from MUXOUT.

        Returns
        -------
        bool
            True when MUXOUT reads high (locked).

        Raises
        ------
        RuntimeError
            If the device has no MUXOUT pin configured.
        """
        return bool(self._device.read_muxout())

    def wait_locked(self, timeout_us=100_000):
        """
        Poll lock detect until locked or timeout.

        Parameters
        ----------
        timeout_us : int
            Maximum wait in microseconds (default 100 ms).

        Returns
        -------
        bool
            True if lock was detected before timeout.
        """
        deadline = _ticks_us() + timeout_us
        while _ticks_diff(_ticks_us(), deadline) < 0:
            if self.is_locked():
                return True
            _sleep_us(100)
        return self.is_locked()

    def mute(self):
        """Disable RF output (``rf_enable=False``)."""
        self._regfile.configure(rf_enable=False)
        if self._powered:
            self._write_stale_registers()

    def unmute(self):
        """Enable RF output (``rf_enable=True``)."""
        self._regfile.configure(rf_enable=True)
        if self._powered:
            self._write_stale_registers()

    def set_output_power(self, code):
        """
        Set RF output power code (R4 DB5:DB4).

        Parameters
        ----------
        code : int
            One of ``consts.REG4_POWER_*`` values.
        """
        self._regfile.configure(output_power=code)
        if self._powered:
            self._write_stale_registers()

    def _solve(self, hz, *, options=None):
        """
        Run the frequency solver with this synthesizer's reference path.

        Parameters
        ----------
        hz : int
            Target frequency in hertz.
        options : SolveOptions or None
            Overrides; defaults to ``self._solve_options``.

        Returns
        -------
        SolveResult

        Notes
        -----
        In low-spur noise mode the solver is asked for MOD >= 50, the data
        sheet minimum for that mode (p.23).
        """
        opts = options or self._solve_options
        if self._regfile.config.noise_mode == consts.REG2_LOW_SPUR:
            opts = opts.copy(mod_min=max(opts.mod_min or 0, LOW_SPUR_MOD_MIN))
        return solve(hz, self._ref_hz, self._profile, options=opts)

    def _apply_solve(self, hz):
        """
        Run the solver and apply fields to the register file.

        Parameters
        ----------
        hz : int
            Target frequency in hertz.

        Returns
        -------
        SolveResult
        """
        result = self._solve(hz)
        self._regfile.configure(**result.fields)
        self._target_hz = hz
        self._achieved_hz = result.achieved_hz
        return result

    def _enable_fast_hop_mode(self):
        """
        Apply register settings for fast frequency hopping.

        Called by ``ADF435xSweeper`` on first playback. Idempotent.
        """
        if self._fast_hop_mode:
            return
        self._regfile.configure(
            double_buffer=True,
            ldp=consts.REG2_LDP_6NS,
        )
        self._fast_hop_mode = True

    def _write_stale_registers(self, *, all_registers=False):
        """
        Send pending register-file changes to the device over SPI.

        Parameters
        ----------
        all_registers : bool
            When True, send the full R5..R0 power-up plan.
        """
        if all_registers:
            plan = self._regfile.commit_all_plan()
        else:
            plan = self._regfile.commit_plan()
        if plan:
            self._write_prebuilt_plan(plan)

    def _write_prebuilt_plan(self, words):
        """
        Send a pre-encoded commit plan to the device over SPI.

        Parameters
        ----------
        words : list of int
            Register words in R5..R0 write order.
        """
        try:
            self._device.write_registers(words)
            self._regfile.mark_written()
            self._last_write_us = _ticks_us()
        except Exception:
            self._regfile.mark_write_failed()
            raise


def _ticks_diff(a, b):
    """
    Difference between two ``ticks_us`` values.

    MicroPython-safe wrapper around ``time.ticks_diff``.
    """
    try:
        return time.ticks_diff(a, b)
    except AttributeError:
        return a - b


def _sleep_us(us):
    """Sleep for microseconds; MicroPython and CPython compatible."""
    try:
        time.sleep_us(us)
    except AttributeError:
        time.sleep(us / 1_000_000.0)
