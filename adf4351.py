# adf4351.py
from machine import Pin, SPI
import time
import math

class ADF4351:
    def __init__(self, spi, le_pin, ce_pin=None, reference_hz=25000000):
        self.spi = spi
        self.le = Pin(le_pin, Pin.OUT)
        self.le.value(0)
        self.reference = reference_hz
        
        if ce_pin is not None:
            self.ce = Pin(ce_pin, Pin.OUT)
            self.ce.value(1)
        
        # Initialize registers with default values
        self.regs = [0] * 6
        self._init_default_registers()
        
    def _init_default_registers(self):
        # These are safe defaults for a 25 MHz reference
        self.regs[5] = 0x580005  # Register 5: Control
        self.regs[4] = 0x80003C  # Register 4: Output config
        self.regs[3] = 0x4B3     # Register 3: Clock divider
        self.regs[2] = 0x4E42    # Register 2: PFD settings
        self.regs[1] = 0x8008029 # Register 1: MOD/Phase
        self.regs[0] = 0x400000  # Register 0: Frequency
        self._write_all_registers()
    
    def _write_register(self, reg_value):
        self.le.value(0)
        # Send 32 bits (4 bytes), MSB first
        for i in range(3, -1, -1):
            byte = (reg_value >> (8 * i)) & 0xFF
            self.spi.write(bytes([byte]))
        self.le.value(1)
        self.le.value(0)
        time.sleep_us(10)  # Small delay for settling
    
    def _write_all_registers(self):
        # Write registers in descending order (5 to 0)
        for i in range(5, -1, -1):
            self._write_register(self.regs[i])
    
    def set_frequency(self, freq_hz):
        """Set output frequency in Hz (35MHz to 4.4GHz)"""
        # Determine output divider (1, 2, 4, 8, 16, 32, 64)
        output_div = 1
        vco_freq = freq_hz
        while vco_freq < 2200000000 and output_div <= 64:
            output_div *= 2
            vco_freq = freq_hz * output_div
        
        # Calculate PLL settings
        r_divider = 1
        pfd_hz = self.reference / r_divider
        total_n = vco_freq / pfd_hz
        int_n = int(total_n)
        frac_n = total_n - int_n
        
        mod = 4095
        frac_val = int(round(frac_n * mod))
        
        if frac_val >= mod:
            frac_val = 0
            int_n += 1
        
        # Build registers
        reg0 = (int_n << 15) | (frac_val << 3) | 0
        reg1 = (1 << 15) | (mod << 3) | 1  # Phase=1
        reg2 = (r_divider << 14) | 0x4E42
        
        # Register 4: Output divider and power
        div_bits = int(math.log2(output_div))
        reg4 = (div_bits << 15) | (3 << 12) | (1 << 11) | 0x80003C
        
        # Write new configuration
        self._write_register(self.regs[5])
        self._write_register(reg4)
        self._write_register(self.regs[3])
        self._write_register(reg2)
        self._write_register(reg1)
        self._write_register(reg0)
        
        # Store updated registers
        self.regs[4] = reg4
        self.regs[2] = reg2
        self.regs[1] = reg1
        self.regs[0] = reg0
        
        return True
