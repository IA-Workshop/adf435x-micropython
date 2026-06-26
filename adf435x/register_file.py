"""
Register file for the ADF435x family: tracks device configuration state.

The register file holds the words last written to the device and the freshly
encoded "current" words, and computes the minimal, correctly ordered set of
writes needed to bring the device up to date. Staleness is derived by diffing
current against last-written -- the diff is the dirty flag, so it can never fall
out of sync with a hand-maintained flag.

This first layer is the staleness and transaction-ordering engine; it operates
on raw words so it can be tested without a device, a profile, or a clock. The
register mapper and configuration setters plug into ``_update_current`` in a
later layer.
"""


class ADF435xRegisterFile:
    """
    Track register state and emit ordered write transactions.

    The file maintains two sets of six words: ``_current`` (the desired state,
    freshly encoded) and ``_last_written`` (what the device was last given). A
    register is stale when the two differ. ``commit`` returns the stale words in
    write order; ``commit_all`` returns all six unconditionally.
    """

    NUM_REGISTERS = 6

    # Registers carrying double-buffered fields. Per the datasheet, the modulus
    # and phase (R1) and the R counter, reference doubler, reference
    # divide-by-2, and charge-pump current (R2) latch only on a subsequent write
    # to R0. So whenever one of these registers changes, R0 must also be
    # written, even if R0 itself is unchanged. R4's divider select is
    # double-buffered only when R2 DB13 is set, which this file leaves disabled,
    # so R4 takes effect on its own write and is excluded here.
    _DOUBLE_BUFFERED = (1, 2)

    def __init__(self) -> None:
        self._current = [0] * self.NUM_REGISTERS
        # None means "never written"; every register starts stale.
        self._last_written = [None] * self.NUM_REGISTERS

    def _update_current(self, words) -> None:
        """Replace the current (desired) words.

        This is the seam the register mapper plugs into: a later layer encodes
        the configuration into six words and calls this. It does not touch
        ``_last_written``, so the change shows up as staleness until committed.

        Parameters
        ----------
        words : sequence of int
            Exactly ``NUM_REGISTERS`` register words, indexed R0..R5.

        Raises
        ------
        ValueError
            If the wrong number of words is supplied.
        """
        if len(words) != self.NUM_REGISTERS:
            raise ValueError(
                "expected %d words, got %d" % (self.NUM_REGISTERS, len(words)))
        self._current = list(words)

    def stale_indices(self) -> list:
        """Return the register indices whose current word differs from the last
        written one, in ascending order.

        Returns
        -------
        list of int
            Indices in [0, NUM_REGISTERS) that need writing.
        """
        return [i for i in range(self.NUM_REGISTERS)
                if self._current[i] != self._last_written[i]]

    def is_stale(self) -> bool:
        """Return True if any register needs writing."""
        return bool(self.stale_indices())

    def commit(self) -> list:
        """Compute the minimal ordered transaction and mark it as written.

        Stale registers are returned as ``(index, word)`` pairs ordered R5 down
        to R0, so R0 is written last. If any double-buffered register changed,
        R0 is added to the set so its write latches the buffered fields.

        This is optimistic: it advances the last-written cache assuming the
        caller will write the returned words to the device.

        Returns
        -------
        list of (int, int)
            ``(register_index, word)`` pairs in write order. Empty if nothing
            is stale.
        """
        stale = set(self.stale_indices())
        if not stale:
            return []
        if stale.intersection(self._DOUBLE_BUFFERED):
            stale.add(0)
        plan = [(i, self._current[i]) for i in sorted(stale, reverse=True)]
        self._last_written = list(self._current)
        return plan

    def commit_all(self) -> list:
        """Return all six words as the full power-up transaction (R5 -> R0).

        Unlike ``commit``, this ignores staleness and always emits every
        register, for the initial power-up programming sequence. It also marks
        everything as written.

        Returns
        -------
        list of (int, int)
            All ``NUM_REGISTERS`` ``(register_index, word)`` pairs, ordered R5
            down to R0.
        """
        plan = [(i, self._current[i])
                for i in range(self.NUM_REGISTERS - 1, -1, -1)]
        self._last_written = list(self._current)
        return plan