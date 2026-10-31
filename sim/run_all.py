#!/usr/bin/env python3
"""Run every simulation of the LiDAR power board in ngspice and check the results.

    python3 sim/run_all.py          # all blocks
    python3 sim/run_all.py buck     # only tests whose name contains "buck"

Each netlist is plain SPICE with .meas lines, so it also opens in LTspice.
This script copies a netlist to a temporary folder, changes .param values where a
test needs it, runs `ngspice -b`, reads the .meas results and compares them with
the limits below. The waveforms used for the plots are written to sim/waves/.
Exit code 0 means every check passed.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WAVES = os.path.join(HERE, 'waves')

# (test name, netlist, {param: value}, signals to save or None, [(measure, low, high, unit, meaning)])
TESTS = [
    ('input protection: 12 V connected correctly', 'input_protection.cir', {'VIN': 12}, None, [
        ('v_after', 11.4, 11.9, 'V', 'voltage left for the buck after the diode'),
        ('i_in', 0.4, 0.5, 'A', 'input current (buck drawing 5.3 W)'),
        ('p_diode', 0, 0.25, 'W', 'diode loss, no heatsink needed'),
    ]),
    ('input protection: 12 V connected reversed', 'input_protection.cir', {'VIN': -12}, None, [
        ('v_after', -0.1, 0.1, 'V', 'the board sees almost nothing'),
        ('i_in', -1e-3, 1e-3, 'A', 'only diode leakage flows'),
    ]),
    ('level shifter: 3.3 V <-> 5 V at 115200 baud', 'level_shifter.cir', {}, 'v(lv) v(hv)', [
        ('hv_low1', 0, 0.4, 'V', '5 V side low when the FPGA sends 0'),
        ('hv_high1', 4.5, 5.01, 'V', '5 V side high when the FPGA sends 1'),
        ('lv_low2', 0, 0.4, 'V', '3.3 V side low when the LiDAR sends 0'),
        ('lv_high2', 2.97, 3.35, 'V', '3.3 V side high when the LiDAR sends 1'),
        ('trise_hv', 0, 2.2e-6, 's', 'rise time well under a bit (8.68 µs)'),
        ('trise_lv', 0, 2.2e-6, 's', 'rise time well under a bit (8.68 µs)'),
    ]),
    ('motor driver: PWM duty 0.6', 'motor_driver.cir', {'DUTY': 0.6}, 'v(pwm) v(d) i(Lm)', [
        ('imot', 0.07, 0.12, 'A', 'average motor current'),
        ('vdmax', 0, 5.6, 'V', 'drain clamped by the flyback diode'),
        ('pmos', 0, 0.05, 'W', 'MOSFET dissipation, no heatsink needed'),
    ]),
    ('motor driver: full speed (duty 1)', 'motor_driver.cir', {'DUTY': 0.999}, None, [
        ('imot', 0.27, 0.31, 'A', 'stall-free full-speed current'),
        ('pmos', 0, 0.05, 'W', 'MOSFET dissipation'),
    ]),
    ('current sense: 0.2 A then 1 A', 'current_sense.cir', {'ILOAD': 1}, 'v(adc)', [
        ('vadc_02', 0.19, 0.21, 'V', '1 V per A at 0.2 A'),
        ('vadc_1', 0.98, 1.02, 'V', '1 V per A at 1 A (XADC full scale)'),
    ]),
    ('buck (averaged): start-up, load steps, 9-15 V input', 'buck_averaged.cir', {}, 'v(out) v(ea) i(L1)', [
        ('v_light', 4.95, 5.05, 'V', 'regulation at 0.2 A'),
        ('v_heavy', 4.95, 5.05, 'V', 'regulation at 1 A'),
        ('v_min_step', 4.75, 5.05, 'V', 'dip after the 0.2 -> 1 A step (5 % limit)'),
        ('v_max_unload', 4.95, 5.25, 'V', 'peak after the 1 -> 0.2 A step (5 % limit)'),
        ('v_vin9', 4.95, 5.05, 'V', 'regulation at 9 V input'),
        ('v_vin15', 4.95, 5.05, 'V', 'regulation at 15 V input'),
        ('v_overshoot', 4.9, 5.5, 'V', 'start-up overshoot (LiDAR absolute max 5.5 V)'),
        ('t_up', 1e-3, 4e-3, 's', 'soft-start time to 4.95 V'),
    ]),
    ('buck (switching): 100 kHz at 1 A', 'buck_switching.cir', {}, 'v(sw) i(L1) v(out)', [
        ('vout', 4.95, 5.05, 'V', 'average output'),
        ('vpp', 0, 0.05, 'V', 'output ripple peak-to-peak'),
        ('ilpp', 0.2, 0.4, 'A', 'coil ripple (design 0.3 A)'),
        ('ilavg', 0.98, 1.02, 'A', 'average coil current = load current'),
        ('duty', 0.8, 0.95, 'V', 'error-amp output (duty = V/2 ≈ 0.43)'),
    ]),
]
DERIVED = {  # extra checks computed from measures of the same test
    'buck_switching.cir': [('efficiency', lambda m: m['pout'] / m['pin'], 0.88, 1.0, '', 'Pout / Pin')],
}

NUM = r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?'


def prepare(src, params, save, tmp):
    text = open(os.path.join(HERE, src)).read()
    for k, v in params.items():
        text, n = re.subn(rf'(\.param\s+{k}\s*=\s*)\S+', rf'\g<1>{v}', text, flags=re.I)
        if n == 0:
            raise SystemExit(f'{src}: no .param {k}')
    if save:
        wave = os.path.join(tmp, 'wave.txt')
        ctl = f'.control\nset wr_singlescale\nset wr_vecnames\nrun\nwrdata {wave} {save}\n.endc\n'
        text = re.sub(r'^\.end\s*$', ctl + '.end', text, flags=re.M | re.I)
    path = os.path.join(tmp, src)
    open(path, 'w').write(text)
    return path


def run(test, tmp):
    name, src, params, save, checks = test
    path = prepare(src, params, save, tmp)
    out = subprocess.run(['ngspice', '-b', path], cwd=tmp, capture_output=True, text=True, timeout=900)
    log = out.stdout + out.stderr
    meas = {}
    for line in log.splitlines():
        m = re.match(rf'^\s*(\w+)\s*=\s*({NUM})', line)
        if m:
            meas[m.group(1).lower()] = float(m.group(2))
    return meas, log, (os.path.join(tmp, 'wave.txt') if save else None)


def fmt(v, unit):
    if unit == 's':
        return f'{v * 1e6:.2f} µs' if v < 1e-3 else f'{v * 1e3:.2f} ms'
    if unit == '':
        return f'{v * 100:.1f} %'
    if v != 0 and abs(v) < 1e-3:
        return f'{v * 1e6:.3g} µ{unit}'
    if v != 0 and abs(v) < 0.1:
        return f'{v * 1e3:.3g} m{unit}'
    return f'{v:.4g} {unit}'


def main():
    if not shutil.which('ngspice'):
        raise SystemExit('ngspice not found: install it (apt install ngspice / brew install ngspice) or open the .cir files in LTspice')
    pick = sys.argv[1] if len(sys.argv) > 1 else ''
    os.makedirs(WAVES, exist_ok=True)
    fails = total = 0
    for test in TESTS:
        name, src = test[0], test[1]
        if pick and pick not in name and pick not in src:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            meas, log, wave = run(test, tmp)
            if wave and os.path.exists(wave):
                shutil.copy(wave, os.path.join(WAVES, src.replace('.cir', '.txt')))
        print(f'\n{name}  [{src}]')
        rows = [(k, meas.get(k), lo, hi, u, why) for k, lo, hi, u, why in test[4]]
        for k, fn, lo, hi, u, why in DERIVED.get(src, []):
            try:
                rows.append((k, fn(meas), lo, hi, u, why))
            except (KeyError, ZeroDivisionError):
                rows.append((k, None, lo, hi, u, why))
        for k, v, lo, hi, u, why in rows:
            total += 1
            ok = v is not None and lo <= v <= hi
            fails += not ok
            val = 'missing' if v is None else fmt(v, u)
            print(f'  {"PASS" if ok else "FAIL"}  {k:<13} {val:>12}   limits {fmt(lo, u)} .. {fmt(hi, u)}   {why}')
        if any(r[1] is None for r in rows):
            print('  ngspice output (last lines):\n    ' + '\n    '.join(log.strip().splitlines()[-15:]))
    print(f'\n{total - fails}/{total} checks passed')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
