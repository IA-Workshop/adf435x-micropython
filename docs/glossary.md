# Glossary

| Term | Meaning | In the library |
|------|---------|----------------|
| ABP | Antibacklash pulse width: 6 ns for fractional-N, 3 ns for integer-N (fixed on the ADF4350) | `abp` |
| Band select | Automatic choice of the VCO sub-band, run on every R0 write; clocked at ≤ 125 kHz, or ≤ 500 kHz in the ADF4351's fast mode | `band_clk_div`, `band_clk_mode` |
| CE | Chip enable pin; low powers down and keeps register contents | `power_up()`, `power_down()` |
| Charge cancel | ADF4351 option that reduces integer-N spurs | `charge_cancel` |
| CP current | Charge-pump current; must suit the loop filter | `cp_current_code` |
| Double buffering | Some fields take effect only on the next R0 write: phase and MOD (R1); doubler, divide-by-2, R counter and CP current (R2); the RF divider (R4) when enabled | `double_buffer` |
| fPFD | Phase-detector comparison frequency, REFIN × doubler ÷ (R × divide-by-2); at most 32 MHz | `f_pfd_hz` |
| FRAC | Fractional numerator of N; 0 means integer-N | `frac` |
| INT | Integer part of N | `int_n` |
| Integer-N / fractional-N | FRAC = 0 / FRAC > 0 | |
| LDF, LDP | Lock-detect cycle count (40 or 5) and comparison window (10 or 6 ns) | `ldf`, `ldp` |
| LE | Load enable pin; a rising edge latches the 32 bits just shifted in | `ADF435xDevice` |
| Lock detect | MUXOUT high when the loop has settled | `is_locked()`, `wait_locked()` |
| MOD | Fractional modulus, 2 to 4095; the output step is fPFD ÷ MOD ÷ RF divider | `mod` |
| MUXOUT | Multipurpose output pin; digital lock detect by default | `muxout` |
| N | Feedback divide ratio INT + FRAC/MOD; fVCO = fPFD × N | |
| Prescaler | 4/5 or 8/9 dual-modulus prescaler; 8/9 needed above 3.6 GHz (ADF4351) or 3.0 GHz (ADF4350) | `prescaler` |
| R counter | Reference divider, 1 to 1023 | `r_counter` |
| REFIN | Reference clock input | `ref_hz` |
| RF divider | Output divider, 1 to 64 (ADF4351) or 16 (ADF4350), a power of two | `rf_divider` |
| Register file | The library's copy of the six registers and what was last written | `ADF435xRegisterFile` |
| VCO | Voltage-controlled oscillator, 2.2 to 4.4 GHz | `vco_hz` |
