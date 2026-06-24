from micropython import const

WORD_SIZE_BYTES = const(4)

# Register Addresses
REG0_ADDR = const(0)
REG1_ADDR = const(1)
REG2_ADDR = const(2)
REG3_ADDR = const(3)
REG4_ADDR = const(4)
REG5_ADDR = const(5)
REG_ADDRS = (REG0_ADDR, REG1_ADDR, REG2_ADDR, REG3_ADDR, REG4_ADDR, REG5_ADDR)

# Register Field Patterns
REG2_LOW_NOISE = const(0b00)
REG2_LOW_SPUR = const(0b11)

REG2_MUX_THREESTATE  = const(0b000)
REG2_MUX_DVDD        = const(0b001)
REG2_MUX_DGND        = const(0b010)
REG2_MUX_RCOUNTER    = const(0b011)
REG2_MUX_NDIVIDER    = const(0b100)
REG2_MUX_ANALOGLOCK  = const(0b101)
REG2_MUX_DIGITALLOCK = const(0b110)

REG3_CLOCKDIV_OFF = const(0b00)
REG3_CLOCKDIV_FASTLOCK = const(0b01)
REG3_CLOCKDIV_RESYNC = const(0b10)

REG5_LOCK_LOW = const(0b00)
REG5_LOCK_DIGITAL = const(0b01)
REG5_LOCK_HIGH = const(0b11)
