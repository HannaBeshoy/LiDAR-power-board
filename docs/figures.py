"""Draw the schematics and plots in docs/img/.

    python3 sim/run_all.py      # first: writes the waveforms to sim/waves/
    python3 docs/figures.py

Needs schemdraw and matplotlib (pip install schemdraw matplotlib).
"""
import os
import re
import numpy as np
import schemdraw
import schemdraw.elements as e
import schemdraw.flow as flow

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, 'img')
WAVES = os.path.join(HERE, '..', 'sim', 'waves')
os.makedirs(IMG, exist_ok=True)
schemdraw.use('svg')


def save(d, name):
    svg = d.get_imagedata('svg').decode()
    svg = re.sub(r'<\?xml[^>]*>', '', svg)
    # white background so the drawing reads on GitHub in light and dark mode
    svg = re.sub(r'(<svg[^>]*>)', r'\1<rect width="100%" height="100%" fill="white"/>', svg, count=1)
    open(os.path.join(IMG, name + '.svg'), 'w').write(svg)
    print('wrote docs/img/' + name + '.svg')


def D(unit=2.5):
    d = schemdraw.Drawing(show=False)
    d.config(unit=unit, fontsize=12, lw=1.5)
    return d


# ------------------------------------------------------------------ block diagram
d = D()
d.config(fontsize=11)
B = dict(w=3.2, h=1.3)
X = [0, 4.6, 9.2, 13.8, 18.4]
d += (src := flow.Box(**B).at((X[0], 0)).anchor('W').label('12 V input\n(bench / 3S battery)'))
d += (prot := flow.Box(**B).at((X[1], 0)).anchor('W').label('1 Input protection\nSS34 + 100 µF'))
d += (buck := flow.Box(**B).at((X[2], 0)).anchor('W').label('2 Buck converter\n12 V → 5 V, 1 A'))
d += (sense := flow.Box(**B).at((X[3], 0)).anchor('W').label('5 Current sense\n0.1 Ω + diff. amp'))
d += (lidar := flow.Box(**B).at((X[4], 0)).anchor('W').label('2D LiDAR\n5 V core + motor'))
for a, b in ((src, prot), (prot, buck), (buck, sense), (sense, lidar)):
    d += flow.Arrow().at(a.E).to(b.W)
d += (mot := flow.Box(**B).at((X[4] + 1.6, -3)).anchor('N').label('4 Motor driver\nlow-side MOSFET'))
d += (ls := flow.Box(**B).at((X[4] + 6.2, -3)).anchor('N').label('3 Level shifter\n3.3 V ↔ 5 V'))
d += (fpga := flow.Box(w=X[4] + 9.4 - X[2], h=1.3).at((X[2], -6.2)).anchor('NW').label('Nexys 4 DDR FPGA (3.3 V I/O)'))
d += flow.Arrow().at(mot.N).to(lidar.S)
d += e.Label().at((mot.N[0] + 0.2, (mot.N[1] + lidar.S[1]) / 2)).label('motor', fontsize=9, halign='left')
d += flow.Arrow().at((mot.S[0], fpga.N[1])).to(mot.S)
d += e.Label().at((mot.S[0] + 0.2, (mot.S[1] + fpga.N[1]) / 2)).label('PWM 25 kHz', fontsize=9, halign='left')
d += flow.Arrow().at(sense.S).to((sense.S[0], fpga.N[1]))
d += e.Label().at((sense.S[0] + 0.2, (sense.S[1] + fpga.N[1]) / 2)).label('XADC, 1 V per A', fontsize=9, halign='left')
d += flow.Line().at(ls.N).toy(lidar.E[1])
d += flow.Arrow().tox(lidar.E[0])
d += flow.Arrow().at(ls.S).to((ls.S[0], fpga.N[1]))
d += e.Label().at((ls.S[0] + 0.2, (ls.S[1] + fpga.N[1]) / 2)).label('UART 3.3 V', fontsize=9, halign='left')
d += e.Label().at((ls.N[0] + 0.2, (ls.N[1] + lidar.E[1]) / 2)).label('UART 5 V', fontsize=9, halign='left')
d += flow.Arrow().at((ls.S[0] - 0.6, fpga.N[1])).to((ls.S[0] - 0.6, ls.S[1]))
save(d, 'block_diagram')

# ------------------------------------------------------------------ power stage (blocks 1 + 2)
d = D()
d += (vin := e.SourceV().up().label('Vin 9–15 V'))
d += e.Diode().right().label('D0 SS34\nreverse polarity', loc='top')
d += (n1 := e.Dot())
d += e.Capacitor(polar=True).down().label('C0\n100 µF', loc='bottom')
d += e.Line().left().to(vin.start)
d += e.Line().at(n1.center).right(1.5)
d += e.Switch(action='close').right().label('S1 MOSFET\n(PWM)', loc='top')
d += (sw := e.Dot().label('SW', loc='top', ofst=0.15))
d += e.Inductor2(loops=3).right().label('L1 100 µH', loc='top')
d += (out := e.Dot().label('5 V out', loc='top'))
d += e.Capacitor().down().label('C1 47 µF\nESR ≤ 0.1 Ω', loc='bottom')
d += (g2 := e.Line().left().tox(sw.center))
d += e.Line().left().tox(n1.center)
d += e.Line().left().tox(vin.start)
d += e.Diode().at(g2.end).up().label('D1 SS34', loc='bottom').to(sw.center)
d += e.Line().at(out.center).right(3.2)
d += (o2 := e.Dot())
d += e.Resistor().down().label('LiDAR\n0.2–1 A', loc='bottom')
d += e.Line().left().tox(out.center)
d += e.Ground().at(vin.start)
d += e.Line().at(o2.center).right(2.2)
d += e.Resistor().down(1.8).label('R1 10k', loc='bottom')
d += (fb := e.Dot())
d += e.Line().right(0.8)
d += e.Dot(open=True).label('FB', loc='right')
d += e.Resistor().at(fb.center).down(1.8).label('R2 10k', loc='bottom')
d += e.Ground()
save(d, 'power_stage')

# ------------------------------------------------------------------ controller (type III error amp + PWM comparator)
d = D(2.2)
d += (op := e.Opamp(leads=True).label('EA', loc='center', ofst=(-0.35, 0)))
inm_x = op.in1[0] - 2.0
d += e.Line().at(op.in1).tox(inm_x)
d += (inm := e.Dot())
d += e.Resistor().left(3.4).label('R1 10k', loc='bottom')
d += (vo := e.Dot().label('Vout', loc='left'))
d += e.Resistor().at(inm.center).down().label('R2 10k', loc='top')
d += e.Ground()
d += e.Line().at(op.in2).left(0.7)
d += e.SourceV().down().reverse().label('Vref 2.5 V\nsoft-start', loc='bottom')
d += e.Ground()
# R3 + C3 in parallel with R1
d += e.Line().at(inm.center).up(1.5)
d += (j1 := e.Dot())
d += e.Capacitor().left(1.7).label('C3 6.8n', loc='top')
d += e.Resistor().left().tox(vo.center).label('R3 680', loc='top')
d += e.Line().down().toy(vo.center)
# feedback Rz + Cz, with Cp in parallel
d += e.Line().at(j1.center).up(1.5)
d += (j2 := e.Dot())
ea_x = op.out[0] + 0.6
d += e.Resistor().right(1.9).label('Rz 10k', loc='top')
d += e.Capacitor().right().tox(ea_x).label('Cz 33n', loc='top')
d += e.Line().at(j2.center).up(1.4)
d += e.Capacitor().right().tox(ea_x).label('Cp 330p', loc='top')
d += e.Line().down().toy(op.out)
d += e.Line().at(op.out).tox(ea_x)
d += (ea := e.Dot().label('V(ea)', loc='top', ofst=(0.45, 0)))
# PWM comparator
d += e.Line().at(ea.center).right(1.6)
d += (cmp_ := e.Opamp(leads=True).anchor('in2').label('PWM', loc='center', ofst=(-0.35, 0)).flip())
d += e.Line().at(cmp_.in1).left(0.6)
d += e.SourceSquare().down().label('triangle 0–2 V\n100 kHz', loc='top')
d += e.Ground()
d += e.Line().at(cmp_.out).right(0.8)
d += e.Dot(open=True).label('gate of S1', loc='right')
save(d, 'controller')

# ------------------------------------------------------------------ level shifter (block 3)
d = D()
# theta -90 + reverse: source on the left, drain on the right, gate on top
d += (m := e.NFet(bulk=False).theta(-90).reverse().at((0, 0)))
d += e.Label().at((m.source[0] + 0.75, m.source[1] - 0.6)).label('M1 BSS138', fontsize=11)
d += e.Line().at(m.source).left(2)
d += (lv := e.Dot())
d += e.Line().left(1.2)
d += e.Dot(open=True).label('LV: FPGA\n3.3 V side', loc='left')
d += e.Line().at(m.drain).right(2)
d += (hv := e.Dot())
d += e.Line().right(1.2)
d += e.Dot(open=True).label('HV: LiDAR\n5 V side', loc='right')
d += e.Resistor().at(lv.center).up(2.6).label('Rp1 10k', loc='top')
d += (r33 := e.Dot().label('3.3 V', loc='top'))
d += e.Resistor().at(hv.center).up(2.6).label('Rp2 10k', loc='bottom')
d += e.Dot().label('5 V', loc='top')
d += e.Line().at(m.gate).toy(r33.center)
d += e.Line().tox(r33.center)
save(d, 'level_shifter')

# ------------------------------------------------------------------ motor driver (block 4)
d = D()
d += (v5 := e.Dot().label('5 V', loc='left'))
d += e.Line().right(2)
d += (tr := e.Dot())
d += e.Motor().down().label('scan motor\n10 Ω, 1 mH', loc='top')
d += (dn := e.Dot())
d += e.Line().at(tr.center).right(2)
d += e.Diode().down().reverse().toy(dn.center).label('Dfly SS14', loc='bottom')
d += e.Line().tox(dn.center)
d += (m := e.NFet(bulk=False).theta(0).reverse().anchor('drain').at(dn.center).label('M2 AO3400', loc='right', ofst=0.3))
d += e.Ground().at(m.source)
d += e.Resistor().at(m.gate).left().label('Rg 100 Ω', loc='top')
d += (gn := e.Dot())
d += e.Line().left(1.2)
d += e.Dot(open=True).label('FPGA PWM\n3.3 V, 25 kHz', loc='left')
d += e.Resistor().at(gn.center).down().label('Rpd 100k', loc='top')
d += e.Ground()
save(d, 'motor_driver')

# ------------------------------------------------------------------ current sense (block 5)
d = D(2.2)
d += (vi := e.Dot().label('5 V from buck', loc='left'))
d += e.Resistor().right(3.0).label('Rsh 0.1 Ω', loc='top')
d += (vl := e.Dot().label('5 V to LiDAR', loc='right'))
op = e.Opamp(leads=True).label('op-amp\n12 V', loc='center', fontsize=9, ofst=(-0.3, 0))
op_in1_rel = (-1.27 - 0.6, 0.5)  # placeholder, moved below
d += (op := op.at((vl.center[0] + 3.6, vl.center[1] - 4.0)).anchor('center'))
# + input from the supply side of the shunt: Ra, Rb divider
d += e.Resistor().at(vi.center).down(2.2).label('Ra 10k', loc='top')
d += e.Line().down().toy(op.in2)
d += (p := e.Dot())
d += e.Line().tox(op.in2)
d += e.Resistor().at(p.center).down(1.8).label('Rb 100k', loc='top')
d += e.Ground()
# − input from the load side: Rc, feedback Rf
d += e.Resistor().at(vl.center).down(2.2).label('Rc 10k', loc='top')
d += e.Line().down().toy(op.in1)
d += e.Line().tox(op.in1[0] - 0.4)
d += (n := e.Dot())
d += e.Line().tox(op.in1)
d += e.Line().at(n.center).up(1.6)
d += e.Resistor().right().tox(op.out[0] + 0.5).label('Rf 100k', loc='top')
d += e.Line().down().toy(op.out)
d += e.Line().at(op.out).right(0.5)
d += e.Dot()
d += e.Resistor().right().label('1.6 kΩ', loc='top')
d += (a := e.Dot())
d += e.Capacitor().down().label('100 nF', loc='bottom')
d += e.Ground()
d += e.Line().at(a.center).right(0.8)
d += e.Dot(open=True).label('XADC\n1 V/A', loc='right')
save(d, 'current_sense')

# ------------------------------------------------------------------ plots
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size': 10, 'axes.grid': True, 'grid.alpha': 0.3, 'svg.fonttype': 'none'})


def load(name):
    p = os.path.join(WAVES, name + '.txt')
    if not os.path.exists(p):
        print('missing', p, '- run sim/run_all.py first')
        return None
    return np.loadtxt(p, skiprows=1)


def done(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, name + '.svg'))
    plt.close(fig)
    print('wrote docs/img/' + name + '.svg')


w = load('buck_averaged')
if w is not None:
    t, vo, ea, il = w[:, 0] * 1e3, w[:, 1], w[:, 2], w[:, 3]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    a1.plot(t, vo, color='#b4531f')
    a1.axhspan(4.75, 5.25, color='#2b7a4b', alpha=0.08, label='±5 % window')
    a1.set_ylim(0, 5.9); a1.set_ylabel('V(out) (V)'); a1.legend(loc='center right', fontsize=8)
    for x, s in ((2, 'soft-start\nends'), (15, '0.2→1 A'), (22, '1→0.2 A'), (30, 'Vin 12→9 V'), (40, 'Vin 9→15 V')):
        a1.annotate(s, (x, 0.4), fontsize=8, ha='center')
    a2.plot(t, il, color='#2d5d9f')
    a2.set_ylabel('I(L1) (A)'); a2.set_xlabel('time (ms)')
    a1.set_title('Buck converter, averaged model: start-up, load steps, input changes')
    done(fig, 'buck_averaged')
    fig, a = plt.subplots(figsize=(8, 3))
    m = (t > 14.5) & (t < 25)
    a.plot(t[m], vo[m] * 1e3 - 5000, color='#b4531f')
    a.set_ylabel('V(out) − 5 V (mV)'); a.set_xlabel('time (ms)')
    a.set_title('Load step 0.2 A → 1 A at 15 ms and back at 22 ms')
    done(fig, 'buck_load_step')

w = load('buck_switching')
if w is not None:
    t = w[:, 0]
    m = t > t[-1] - 40e-6
    t = (t[m] - t[m][0]) * 1e6
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
    a1.plot(t, w[m, 1], color='#555'); a1.set_ylabel('V(SW) (V)')
    a2.plot(t, w[m, 2], color='#2d5d9f'); a2.set_ylabel('I(L1) (A)')
    a3.plot(t, w[m, 3] * 1e3 - 5000, color='#b4531f'); a3.set_ylabel('V(out) − 5 V (mV)')
    a3.set_xlabel('time (µs)')
    a1.set_title('Buck converter, switching model at 1 A: four periods of 10 µs')
    done(fig, 'buck_switching')

w = load('level_shifter')
if w is not None:
    t = w[:, 0] * 1e6
    fig, a = plt.subplots(figsize=(8, 3.2))
    a.plot(t, w[:, 1], label='3.3 V side (FPGA)', color='#2d5d9f')
    a.plot(t, w[:, 2], label='5 V side (LiDAR)', color='#b4531f', ls='--')
    a.axvline(50, color='grey', lw=0.8)
    a.annotate('FPGA sends', (25, 5.3), ha='center'); a.annotate('LiDAR sends', (75, 5.3), ha='center')
    a.set_ylim(-0.3, 5.8); a.set_xlabel('time (µs)'); a.set_ylabel('V'); a.legend(loc='lower right', fontsize=8)
    a.set_title('Level shifter at 115 200 baud, both directions')
    done(fig, 'level_shifter_wave')

w = load('motor_driver')
if w is not None:
    t = w[:, 0]
    m = t > t[-1] - 120e-6
    t = (t[m] - t[m][0]) * 1e6
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.5), sharex=True)
    a1.plot(t, w[m, 1], label='PWM from FPGA', color='#2d5d9f')
    a1.plot(t, w[m, 2], label='drain D', color='#b4531f')
    a1.set_ylabel('V'); a1.legend(loc='upper right', fontsize=8)
    a2.plot(t, w[m, 3] * 1e3, color='#2b7a4b'); a2.set_ylabel('I(motor) (mA)'); a2.set_xlabel('time (µs)')
    a1.set_title('Motor driver at duty 0.6: drain clamped at 5 V + VD when the MOSFET turns off')
    done(fig, 'motor_driver_wave')
