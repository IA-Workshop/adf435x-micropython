from . import consts as consts

def _check_field(value: int, bits: int, name: str) -> int:
    """
    Validate that an unsigned value fits in a fixed-width field.

    Parameters
    ----------
    value : int
        The value to place in the field.
    bits : int
        Field width in bits.
    name : str
        Field name, used in the error message.

    Returns
    -------
    int
        The validated value, unchanged.

    Raises
    ------
    ValueError
        If ``value`` is negative or does not fit in ``bits`` bits.
    """
    if value < 0 or value >= (1 << bits):
        raise ValueError("%s=%d does not fit in %d bits" % (name, value, bits))
    return value

def _reg0_encode(int_n: int, frac: int) -> int:

    # Validate fields are in-bounds
    _check_field(int_n, 16, "INT")
    _check_field(frac, 12, 'FRAC')

    word = 0x0
    word |= int_n << 15  # DB[30:15] --> INT Value
    word |= frac << 3    # DB[14:3] --> FRAC Value
    word |= consts.REG_ADDRS[0] # DB[2:0] --> Register address = 0b000

    return word

def _reg1_encode(mod: int,
                 prescaler: int,
                 phase: int,
                 phase_adjust: bool) -> int:
    # Validate fields are in-bounds
    _check_field(mod, 12, "MOD")
    _check_field(phase, 12, "phase")

    word = 0x0
    word |= int(phase_adjust) << 28
    word |= prescaler << 27
    word |= phase << 15
    word |= mod << 3
    word |= consts.REG_ADDRS[1] # DB[2:0] --> Register address = 0b001

    return word

def _reg2_encode() -> int:
    return 0
