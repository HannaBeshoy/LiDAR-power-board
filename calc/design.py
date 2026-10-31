"""Design calculations for the LiDAR power board.

Every component value in the schematics comes from this file. Run:
    python3 calc/design.py
It prints the design table and writes docs/img/loop_bode.svg (loop gain of the 5 V buck converter).
"""
import os
import numpy as np

E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]


def e12(x):
    """Nearest E12 value."""
    dec = 10 ** np.floor(np.log10(x))
    m = x / dec
    best = min(E12 + [10.0], key=lambda v: abs(np.log(v / m)))
    return best * dec


rows = []


def row(block, item, formula, value, chosen=None):
    rows.append((block, item, formula, value, chosen if chosen is not None else ''))


# ---------------------------------------------------------------- requirements
VIN_NOM, VIN_MIN, VIN_MAX = 12.0, 9.0, 15.0     # bench supply or 3S Li-ion battery
VOUT, IOUT = 5.0, 1.0                            # LiDAR: sensor core + scan motor (typical 2D LiDAR)
FSW = 100e3                                      # switching frequency
RIPPLE_I = 0.30                                  # coil current ripple, fraction of IOUT
VD = 0.35                                        # Schottky drop at 1 A
VRAMP = 2.0                                      # PWM triangle amplitude
VREF = 2.5

# ---------------------------------------------------------------- block 2: buck converter (Topic 6)
D = (VOUT + VD) / (VIN_NOM + VD)
row('Buck', 'duty cycle (12 V in)', '(Vout + VD) / (Vin + VD)', f'{D:.3f}')
for v in (VIN_MIN, VIN_MAX):
    row('Buck', f'duty cycle ({v:.0f} V in)', '(Vout + VD) / (Vin + VD)', f'{(VOUT + VD) / (v + VD):.3f}')
dI = RIPPLE_I * IOUT
L = (VIN_NOM - VOUT) * D / (FSW * dI)
Lc = 100e-6
row('Buck', 'inductor L', '(Vin − Vout)·D / (f·ΔI_L), ΔI_L = 0.3 A', f'{L * 1e6:.1f} µH', '100 µH, ≥ 1.5 A saturation')
dI_real = (VIN_MAX - VOUT) * (VOUT + VD) / (VIN_MAX + VD) / (FSW * Lc)
row('Buck', 'worst-case ΔI_L (15 V in)', '(Vin − Vout)·D / (f·L)', f'{dI_real:.3f} A')
dV = 0.02
C = dI / (8 * FSW * dV)
row('Buck', 'output capacitor C (ripple only)', 'ΔI_L / (8·f·ΔV), ΔV = 20 mV', f'{C * 1e6:.1f} µF', '47 µF low-ESR')
ESR = 0.1
row('Buck', 'ripple from ESR', 'ΔI_L · ESR (0.1 Ω)', f'{dI * ESR * 1e3:.0f} mV', 'use ≤ 0.05 Ω for < 20 mV')
f0 = 1 / (2 * np.pi * np.sqrt(Lc * 47e-6))
row('Buck', 'LC resonance f0', '1 / (2π·√(LC))', f'{f0:.0f} Hz')
fesr = 1 / (2 * np.pi * ESR * 47e-6)
row('Buck', 'ESR zero', '1 / (2π·ESR·C)', f'{fesr / 1e3:.1f} kHz')
row('Buck', 'feedback divider', 'Vout = Vref·(1 + R1/R2), Vref = 2.5 V', 'R1/R2 = 1', 'R1 = R2 = 10 kΩ')
row('Buck', 'modulator gain', 'Vin / Vramp', f'{VIN_NOM / VRAMP:.1f}')
row('Buck', 'Schottky loss', 'VD·Iout·(1 − D)', f'{VD * IOUT * (1 - D):.2f} W', 'SS34 (3 A, 40 V)')
row('Buck', 'switch conduction loss', 'Iout²·Ron·D, Ron = 50 mΩ', f'{IOUT ** 2 * 0.05 * D * 1e3:.0f} mW')

# type III compensation (values chosen with the loop search below)
R1, RZ, CZ, CP, R3, C3 = 10e3, 10e3, 33e-9, 330e-12, 680, 6.8e-9
row('Buck', 'compensation zero 1', '1 / (2π·Rz·Cz)', f'{1 / (2 * np.pi * RZ * CZ):.0f} Hz', 'Rz = 10 kΩ, Cz = 33 nF')
row('Buck', 'compensation zero 2', '1 / (2π·(R1 + R3)·C3)', f'{1 / (2 * np.pi * (R1 + R3) * C3):.0f} Hz', 'R3 = 680 Ω, C3 = 6.8 nF')
row('Buck', 'compensation pole 1', '1 / (2π·R3·C3)', f'{1 / (2 * np.pi * R3 * C3) / 1e3:.1f} kHz', '≈ ESR zero')
row('Buck', 'compensation pole 2', '1 / (2π·Rz·Cp)', f'{1 / (2 * np.pi * RZ * CP) / 1e3:.1f} kHz', 'Cp = 330 pF, ≈ fs/2')

f = np.logspace(1, 5.5, 4000)
s = 2j * np.pi * f


def plant(R):
    zc = ESR + 1 / (s * 47e-6)
    zo = 1 / (1 / zc + 1 / R)
    return VIN_NOM / VRAMP * zo / (zo + s * Lc + 0.1)


def comp():
    zin = 1 / (1 / R1 + 1 / (R3 + 1 / (s * C3)))
    zf = 1 / (1 / (RZ + 1 / (s * CZ)) + s * CP)
    return zf / zin


def margins(T):
    mag = np.abs(T)
    i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0][0]
    return f[i], 180 + np.degrees(np.angle(T[i]))


loops = {}
for R, name in ((5, '1 A'), (25, '0.2 A'), (1000, '5 mA')):
    T = comp() * plant(R)
    fc, pm = margins(T)
    loops[name] = T
    row('Buck', f'loop crossover / phase margin ({name})', 'from |T| = 1', f'{fc / 1e3:.1f} kHz / {pm:.0f}°', 'target PM ≥ 45°')

# ---------------------------------------------------------------- block 1: input protection (Topic 4)
row('Input', 'reverse-polarity diode loss', 'VD·Iin, Iin ≈ Pout / (η·Vin)', f'{0.4 * 5 / (0.9 * 12):.2f} W', 'SS34 in series')
row('Input', 'bulk capacitor', 'holds the input during load steps', '—', '100 µF / 25 V')

# ---------------------------------------------------------------- block 3: level shifter (Topic 5)
tbit = 1 / 115200
tau = 10e3 * 60e-12
row('Level shifter', 'bit time at 115 200 baud', '1 / baud', f'{tbit * 1e6:.2f} µs')
row('Level shifter', 'rise time (10 kΩ pull-up, 60 pF)', '2.2·R·C', f'{2.2 * tau * 1e6:.2f} µs', 'BSS138, 10 kΩ pull-ups')
row('Level shifter', 'MOSFET threshold', 'must turn on with 3.3 V gate', 'Vgs(th) ≤ 1.5 V', 'BSS138: 0.8–1.5 V')

# ---------------------------------------------------------------- block 4: motor driver (Topics 5, 6, 11)
FPWM = 25e3
row('Motor driver', 'PWM frequency', 'above hearing (20 kHz)', f'{FPWM / 1e3:.0f} kHz')
Rm, Vemf = 10.0, 2.0
for dd in (0.3, 0.6, 1.0):
    i = max(dd * 5 - Vemf, 0) / Rm
    row('Motor driver', f'motor current at D = {dd}', '(D·5 V − E) / Rm, Rm = 10 Ω, E = 2 V', f'{i * 1e3:.0f} mA')
row('Motor driver', 'gate resistor', 'limits gate current, damps ringing', '—', '100 Ω')
row('Motor driver', 'gate pull-down', 'keeps the motor off while the FPGA boots', '—', '100 kΩ')
row('Motor driver', 'MOSFET', 'logic level: fully on at Vgs = 3.3 V', 'Rds(on) < 0.1 Ω at 2.5 V', 'e.g. IRLML6344 / AO3400')
row('Motor driver', 'flyback diode', 'clamps the drain at 5 V + VD when the switch opens', '—', 'SS14 Schottky')

# ---------------------------------------------------------------- block 5: current sense (Topic 8)
RSH = 0.1
G = 10
row('Current sense', 'shunt voltage at 1 A', 'I·Rsh', f'{RSH * 1e3:.0f} mV', '0.1 Ω, 0.25 W, 1 %')
row('Current sense', 'shunt loss at 1 A', 'I²·Rsh', f'{RSH * 1e3:.0f} mW')
row('Current sense', 'difference amplifier gain', 'Rf/Rc for 1 V per A (XADC range 0–1 V)', f'{G}', 'Rf = Rb = 100 kΩ, Rc = Ra = 10 kΩ')
row('Current sense', 'output filter cut-off', '1 / (2π·R·C)', f'{1 / (2 * np.pi * 1.6e3 * 100e-9):.0f} Hz', '1.6 kΩ, 100 nF')
row('Current sense', 'op-amp common-mode at the inputs', '5 V · Rb/(Ra + Rb)', f'{5 * 100 / 110:.2f} V', 'op-amp supplied from 12 V')
for tol in (0.01, 0.001):
    acm = 4 * tol * G / (1 + G)
    row('Current sense', f'worst-case zero error, {tol * 100:g} % resistors', 'Acm·Vcm, Acm ≈ 4ε·G/(1 + G)',
        f'{acm * 5 * 1e3:.0f} mV = {acm * 5 / (RSH * G) * 1e3:.0f} mA',
        '0.1 % resistors + zero calibration in the FPGA' if tol == 0.001 else '')

# ---------------------------------------------------------------- output
if __name__ == '__main__':
    w = [14, 40, 46, 18, 30]
    print(' | '.join(h.ljust(n) for h, n in zip(('Block', 'Quantity', 'Formula', 'Value', 'Chosen'), w)))
    print('-' * 160)
    for r in rows:
        print(' | '.join(str(c).ljust(n) for c, n in zip(r, w)))

    md = ['| Block | Quantity | Formula | Value | Chosen |', '| --- | --- | --- | --- | --- |']
    md += [f'| {a} | {b} | {c} | {d} | {e} |' for a, b, c, d, e in rows]
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, '..', 'docs', 'design_table.md'), 'w').write('\n'.join(md) + '\n')

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 5), sharex=True)
        for name, T in loops.items():
            a1.semilogx(f, 20 * np.log10(np.abs(T)), label=f'load {name}')
            a2.semilogx(f, np.degrees(np.unwrap(np.angle(T))))
        a1.axhline(0, color='grey', lw=0.8); a2.axhline(-180, color='grey', lw=0.8)
        a1.set_ylabel('loop gain (dB)'); a2.set_ylabel('phase (°)'); a2.set_xlabel('frequency (Hz)')
        a1.legend(); a1.grid(True, which='both', alpha=0.3); a2.grid(True, which='both', alpha=0.3)
        a1.set_title('5 V buck converter: loop gain with type III compensation')
        fig.tight_layout(); fig.savefig(os.path.join(here, '..', 'docs', 'img', 'loop_bode.svg'))
        print('\nwrote docs/design_table.md and docs/img/loop_bode.svg')
    except ImportError:
        print('\nmatplotlib not installed: skipped the Bode plot')
