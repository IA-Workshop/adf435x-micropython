from machine import Pin, SPI
import time
import math

class ADF4351:
    def __init__(self, spi, le_pin, ce_pin=None, ref_clk_hz=25000000):
        self.spi = spi
        self.le = Pin(le_pin, Pin.OUT)
        self.le.value(0)  # Start LOW
        self.ref_clk = ref_clk_hz
        
        if ce_pin is not None:
            self.ce = Pin(ce_pin, Pin.OUT)
            self.ce.value(1)
        
        # Initialize register array (0-5)
        self.regs = [0] * 6
        
        # Set default register values (from ADF4351 datasheet)
        self.regs[5] = 0x580005   # R5: Lock detect, digital
        self.regs[4] = 0x7C003C   # R4: Output enabled, +5dBm, divider=1
        self.regs[3] = 0x0      # R3: Clock divider off
        self.regs[2] = 0x4E42     # R2: R=1, CP=2.5mA, LDF=1
        self.regs[1] = 0x8008029  # R1: Phase=1, MOD=4095
        self.regs[0] = 0x400000   # R0: Initial frequency
        
        # Write all registers to initialize
        self._write_all_registers()
        
    def _write_register(self, reg_value):
        """Write a single 32-bit register to ADF4351"""
        self.le.value(0)
        time.sleep_us(1)
        
        # Send 4 bytes, MSB first
        for i in range(3, -1, -1):
            byte = (reg_value >> (8 * i)) & 0xFF
            self.spi.write(bytes([byte]))
        
        time.sleep_us(1)
        self.le.value(1)
        time.sleep_us(20)  # Critical: LE must be high for at least 10ns, but 20us is safe
        self.le.value(0)
    
    def _write_all_registers(self):
        """Write all registers in descending order (5 to 0)"""
        for i in range(5, -1, -1):
            self._write_register(self.regs[i])
            time.sleep_us(5)
    
    def set_frequency(self, freq_hz):
        """
        Set output frequency in Hz
        Range: 35MHz to 4.4GHz
        """
        # Step 1: Calculate VCO frequency (must be 2.2-4.4 GHz)
        # Find appropriate output divider
        output_div = 1
        vco_freq = freq_hz
        
        while vco_freq < 2200000000 and output_div <= 64:
            output_div *= 2
            vco_freq = freq_hz * output_div
        
        # Divider bits (0=1, 1=2, 2=4, 3=8, 4=16, 5=32, 6=64)
        div_bits = int(math.log2(output_div))
        
        # Step 2: Calculate PLL parameters
        # Set R divider to 1 (for 25MHz PFD)
        r_div = 1
        pfd_freq = self.ref_clk / r_div  # 25 MHz
        
        # Calculate N divider values
        n_total = vco_freq / pfd_freq
        int_n = int(n_total)
        frac_n = n_total - int_n
        
        # Use MOD = 4095 for fractional resolution
        mod = 4095
        frac_val = int(round(frac_n * mod))
        
        # Handle rounding
        if frac_val >= mod:
            frac_val = 0
            int_n += 1
        
        # Step 3: Build register values
        # Register 0: INT and FRAC
        reg0 = (int_n << 15) | (frac_val << 3) | 0
        
        # Register 1: MOD and Phase
        reg1 = (1 << 15) | (mod << 3) | 1
        
        # Register 2: R counter, CP, etc.
        reg2 = (r_div << 14) | 0x4E42
        
        # Register 4: Output divider, power, enable
        # Bits: [18:15]=div_bits, [14:12]=power(3=+5dBm), [11]=RF enable(1)
        reg4 = (div_bits << 15) | (3 << 12) | (1 << 11) | 0x7C0000 | 4
        
        # Step 4: Update register array
        self.regs[0] = reg0
        self.regs[1] = reg1
        self.regs[2] = reg2
        self.regs[4] = reg4
        
        # Step 5: Write to hardware
        self._write_all_registers()
        
        # Debug output
        print(f"\nFrequency: {freq_hz/1e6:.1f} MHz")
        print(f"  VCO: {vco_freq/1e6:.1f} MHz, Divider: {output_div} (bits={div_bits})")
        print(f"  INT={int_n}, FRAC={frac_val}/{mod}")
        print(f"  R0: 0x{reg0:08X}")
        print(f"  R1: 0x{reg1:08X}")
        print(f"  R2: 0x{reg2:08X}")
        print(f"  R4: 0x{reg4:08X}")
        
        return True
    
    def rf_enable(self, enable):
        """Enable or disable RF output"""
        if enable:
            # Set bit 11 in register 4
            self.regs[4] |= (1 << 11)
        else:
            # Clear bit 11 in register 4
            self.regs[4] &= ~(1 << 11)
        
        # Rewrite register 4 (must write all registers in order)
        self._write_all_registers()
        print(f"RF Output: {'ON' if enable else 'OFF'}")
    
    def set_output_power(self, power_level):
        """
        Set output power level
        0 = -4 dBm
        1 = -1 dBm
        2 = +2 dBm
        3 = +5 dBm
        """
        # Clear power bits (bits 12-14)
        self.regs[4] &= ~(0x7 << 12)
        # Set new power bits
        self.regs[4] |= ((power_level & 0x7) << 12)
        # Rewrite register 4
        self._write_all_registers()
        print(f"Output power set to level {power_level}")
    
    def print_registers(self):
        """Debug: Print current register values"""
        print("\nCurrent Registers:")
        for i in range(6):
            print(f"  R{i}: 0x{self.regs[i]:08X}")
