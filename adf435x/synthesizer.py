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
from .solver import SolveOptions, SolveResult, solve

_TICKS_MS_STUB = 0


def _ticks_ms():
    """
    Return a millisecond timestamp.

    Uses ``time.ticks_ms()`` on MicroPython; a monotonic stub under CPython.
    """
    global _TICKS_MS_STUB
    try:
        return time.ticks_ms()
    except AttributeError:
        _TICKS_MS_STUB += 1
        return _TICKS_MS_STUB


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
        self._last_write_ms = None
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
    def last_write_ms(self):
        """Timestamp of the last successful SPI write, or None."""
        return self._last_write_ms

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

    def wait_locked(self, timeout_ms=100):
        """
        Poll lock detect until locked or timeout.

        Parameters
        ----------
        timeout_ms : int
            Maximum wait in milliseconds.

        Returns
        -------
        bool
            True if lock was detected before timeout.
        """
        deadline = _ticks_ms() + timeout_ms
        while _ticks_diff(_ticks_ms(), deadline) < 0:
            if self.is_locked():
                return True
            _sleep_ms(1)
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
        result = solve(
            hz,
            self._ref_hz,
            self._profile,
            options=self._solve_options,
        )
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
            self._last_write_ms = _ticks_ms()
        except Exception:
            self._regfile.mark_write_failed()
            raise


def _ticks_diff(a, b):
    """
    Difference between two ``ticks_ms`` values.

    MicroPython-safe wrapper around ``time.ticks_diff``.
    """
    try:
        return time.ticks_diff(a, b)
    except AttributeError:
        return a - b


def _sleep_ms(ms):
    """Sleep for milliseconds; MicroPython and CPython compatible."""
    try:
        time.sleep_ms(ms)
    except AttributeError:
        time.sleep(ms / 1000.0)
