| Block | Quantity | Formula | Value | Chosen |
| --- | --- | --- | --- | --- |
| Buck | duty cycle (12 V in) | (Vout + VD) / (Vin + VD) | 0.433 |  |
| Buck | duty cycle (9 V in) | (Vout + VD) / (Vin + VD) | 0.572 |  |
| Buck | duty cycle (15 V in) | (Vout + VD) / (Vin + VD) | 0.349 |  |
| Buck | inductor L | (Vin − Vout)·D / (f·ΔI_L), ΔI_L = 0.3 A | 101.1 µH | 100 µH, ≥ 1.5 A saturation |
| Buck | worst-case ΔI_L (15 V in) | (Vin − Vout)·D / (f·L) | 0.349 A |  |
| Buck | output capacitor C (ripple only) | ΔI_L / (8·f·ΔV), ΔV = 20 mV | 18.8 µF | 47 µF low-ESR |
| Buck | ripple from ESR | ΔI_L · ESR (0.1 Ω) | 30 mV | use ≤ 0.05 Ω for < 20 mV |
| Buck | LC resonance f0 | 1 / (2π·√(LC)) | 2322 Hz |  |
| Buck | ESR zero | 1 / (2π·ESR·C) | 33.9 kHz |  |
| Buck | feedback divider | Vout = Vref·(1 + R1/R2), Vref = 2.5 V | R1/R2 = 1 | R1 = R2 = 10 kΩ |
| Buck | modulator gain | Vin / Vramp | 6.0 |  |
| Buck | Schottky loss | VD·Iout·(1 − D) | 0.20 W | SS34 (3 A, 40 V) |
| Buck | switch conduction loss | Iout²·Ron·D, Ron = 50 mΩ | 22 mW |  |
| Buck | compensation zero 1 | 1 / (2π·Rz·Cz) | 482 Hz | Rz = 10 kΩ, Cz = 33 nF |
| Buck | compensation zero 2 | 1 / (2π·(R1 + R3)·C3) | 2191 Hz | R3 = 680 Ω, C3 = 6.8 nF |
| Buck | compensation pole 1 | 1 / (2π·R3·C3) | 34.4 kHz | ≈ ESR zero |
| Buck | compensation pole 2 | 1 / (2π·Rz·Cp) | 48.2 kHz | Cp = 330 pF, ≈ fs/2 |
| Buck | loop crossover / phase margin (1 A) | from |T| = 1 | 14.3 kHz / 67° | target PM ≥ 45° |
| Buck | loop crossover / phase margin (0.2 A) | from |T| = 1 | 14.5 kHz / 65° | target PM ≥ 45° |
| Buck | loop crossover / phase margin (5 mA) | from |T| = 1 | 14.6 kHz / 65° | target PM ≥ 45° |
| Input | reverse-polarity diode loss | VD·Iin, Iin ≈ Pout / (η·Vin) | 0.19 W | SS34 in series |
| Input | bulk capacitor | holds the input during load steps | — | 100 µF / 25 V |
| Level shifter | bit time at 115 200 baud | 1 / baud | 8.68 µs |  |
| Level shifter | rise time (10 kΩ pull-up, 60 pF) | 2.2·R·C | 1.32 µs | BSS138, 10 kΩ pull-ups |
| Level shifter | MOSFET threshold | must turn on with 3.3 V gate | Vgs(th) ≤ 1.5 V | BSS138: 0.8–1.5 V |
| Motor driver | PWM frequency | above hearing (20 kHz) | 25 kHz |  |
| Motor driver | motor current at D = 0.3 | (D·5 V − E) / Rm, Rm = 10 Ω, E = 2 V | 0 mA |  |
| Motor driver | motor current at D = 0.6 | (D·5 V − E) / Rm, Rm = 10 Ω, E = 2 V | 100 mA |  |
| Motor driver | motor current at D = 1.0 | (D·5 V − E) / Rm, Rm = 10 Ω, E = 2 V | 300 mA |  |
| Motor driver | gate resistor | limits gate current, damps ringing | — | 100 Ω |
| Motor driver | gate pull-down | keeps the motor off while the FPGA boots | — | 100 kΩ |
| Motor driver | MOSFET | logic level: fully on at Vgs = 3.3 V | Rds(on) < 0.1 Ω at 2.5 V | e.g. IRLML6344 / AO3400 |
| Motor driver | flyback diode | clamps the drain at 5 V + VD when the switch opens | — | SS14 Schottky |
| Current sense | shunt voltage at 1 A | I·Rsh | 100 mV | 0.1 Ω, 0.25 W, 1 % |
| Current sense | shunt loss at 1 A | I²·Rsh | 100 mW |  |
| Current sense | difference amplifier gain | Rf/Rc for 1 V per A (XADC range 0–1 V) | 10 | Rf = Rb = 100 kΩ, Rc = Ra = 10 kΩ |
| Current sense | output filter cut-off | 1 / (2π·R·C) | 995 Hz | 1.6 kΩ, 100 nF |
| Current sense | op-amp common-mode at the inputs | 5 V · Rb/(Ra + Rb) | 4.55 V | op-amp supplied from 12 V |
| Current sense | worst-case zero error, 1 % resistors | Acm·Vcm, Acm ≈ 4ε·G/(1 + G) | 182 mV = 182 mA |  |
| Current sense | worst-case zero error, 0.1 % resistors | Acm·Vcm, Acm ≈ 4ε·G/(1 + G) | 18 mV = 18 mA | 0.1 % resistors + zero calibration in the FPGA |
