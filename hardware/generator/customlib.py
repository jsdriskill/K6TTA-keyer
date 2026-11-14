"""Custom footprints and symbols for the K6TTA keyer boards (KiCad 6 syntax, upgraded by newer KiCad)."""


def _pad_th(num, x, y, size=1.7, drill=1.0, shape=None):
    shape = shape or ("rect" if num == "1" else "circle")
    return ('  (pad "%s" thru_hole %s (at %g %g) (size %g %g) (drill %g) (layers *.Cu *.Mask))\n'
            % (num, shape, x, y, size, size, drill))


def _line(x1, y1, x2, y2, layer, w):
    return '  (fp_line (start %g %g) (end %g %g) (layer "%s") (width %g))\n' % (x1, y1, x2, y2, layer, w)


def _rect(x1, y1, x2, y2, layer, w):
    return (_line(x1, y1, x2, y1, layer, w) + _line(x2, y1, x2, y2, layer, w) +
            _line(x2, y2, x1, y2, layer, w) + _line(x1, y2, x1, y1, layer, w))


def _txt(kind, text, x, y, layer):
    return ('  (fp_text %s "%s" (at %g %g) (layer "%s")\n    (effects (font (size 1 1) (thickness 0.15))))\n'
            % (kind, text, x, y, layer))


# RP2040-Zero pin order, counter-clockwise from top-left with the USB-C at the top (top view).
RP2040_ZERO_PINS = ["5V", "GND", "3V3", "GP29", "GP28", "GP27", "GP26", "GP15", "GP14",
                    "GP13", "GP12", "GP11", "GP10", "GP9",
                    "GP8", "GP7", "GP6", "GP5", "GP4", "GP3", "GP2", "GP1", "GP0"]


def rp2040_zero_footprint():
    s = ('(footprint "RP2040-Zero_Socketed" (version 20211014) (generator pcbnew)\n  (layer "F.Cu")\n'
         '  (descr "Waveshare RP2040-Zero on 2.54mm pin sockets (9 + 5 + 9 pins), USB-C at top. Top view.")\n'
         '  (tags "RP2040 Zero Waveshare")\n  (attr through_hole)\n')
    s += _txt("reference", "REF**", 0, -13.5, "F.SilkS")
    s += _txt("value", "RP2040-Zero", 0, 13.5, "F.Fab")
    s += _rect(-9, -11.75, 9, 11.75, "F.SilkS", 0.12)
    s += _rect(-4.5, -12.25, 4.5, -9.25, "F.SilkS", 0.12)
    s += _txt("user", "USB", 0, -7.5, "F.SilkS")
    s += _rect(-9.25, -12.5, 9.25, 12, "F.CrtYd", 0.05)
    s += _rect(-9, -11.75, 9, 11.75, "F.Fab", 0.1)
    pos = []
    for i in range(9):
        pos.append((-7.62, -10.16 + 2.54 * i))
    for i in range(1, 6):
        pos.append((-7.62 + 2.54 * i, 10.16))
    for i in range(9):
        pos.append((7.62, 10.16 - 2.54 * i))
    for n, (x, y) in enumerate(pos, 1):
        s += _pad_th(str(n), x, y)
    return s + ")\n"


def rk10j_footprint():
    """Alps RK10J top-adjust thumbwheel (RK10J11E0034), checked against the Alps PC board drawing.
    Wheel centre at origin, terminals toward +Y. Pads 1/3/5 = datasheet pins 1 (end) / 2 (wiper) / 3 (end);
    pads 2 and 4 are dummy terminals; the two unnumbered slots are mounting tabs."""
    s = ('(footprint "Alps_RK10J_Thumbwheel_5pin" (version 20211014) (generator pcbnew)\n  (layer "F.Cu")\n'
         '  (descr "Alps RK10J thumbwheel potentiometer, 5 terminals P2.0mm, 2 mounting tabs. Checked against Alps drawing: pads 1,3,5 = pins 1 (end), 2 (wiper), 3 (end); pads 2,4 dummy; slots = tabs")\n'
         '  (tags "thumbwheel potentiometer Alps RK10J")\n  (attr through_hole)\n')
    s += _txt("reference", "REF**", 0, -8.5, "F.SilkS")
    s += _txt("value", "RK10J", 0, 0, "F.Fab")
    s += '  (fp_circle (center 0 0) (end 0 -6.5) (layer "F.SilkS") (width 0.12))\n'
    s += '  (fp_circle (center 0 0) (end 0 -7) (layer "F.Fab") (width 0.1))\n'
    for a in [(-3.5, -5, 3.5, -5), (5, -3.5, 5, 6.3), (-5, 6.3, -5, -3.5), (-5, -3.5, -3.5, -5), (5, -3.5, 3.5, -5)]:
        s += _line(*a, "F.Fab", 0.1)
    s += _rect(-7.25, -7.25, 7.25, 8.6, "F.CrtYd", 0.05)
    s += _txt("user", "1", -4, 9.6, "F.SilkS")
    for i in range(5):
        s += _pad_th(str(i + 1), -4 + 2 * i, 7.5, size=1.6, drill=1.0, shape="circle")
    for x in (-5, 5):
        s += ('  (pad "" thru_hole oval (at %g -2.5) (size 1.3 2.0) (drill oval 0.75 1.3) (layers *.Cu *.Mask))\n' % x)
    return s + ")\n"


def _sym_pin(num, name, x, y, ang, length=2.54, etype="passive"):
    return ('      (pin %s line (at %g %g %d) (length %g)\n        (name "%s" (effects (font (size 1.27 1.27))))\n'
            '        (number "%s" (effects (font (size 1.27 1.27)))))\n' % (etype, x, y, ang, length, name, num))


def _sym_head(name, ref, value, fp, desc):
    return ('  (symbol "%s" (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "%s" (id 0) (at 0 0 0) (effects (font (size 1.27 1.27))))\n'
            '    (property "Value" "%s" (id 1) (at 0 0 0) (effects (font (size 1.27 1.27))))\n'
            '    (property "Footprint" "%s" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Datasheet" "~" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "ki_description" "%s" (id 4) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            % (name, ref, value, fp, desc))


def rp2040_zero_symbol(name="RP2040-Zero"):
    s = _sym_head(name, "U", "RP2040-Zero", "K6TTA:RP2040-Zero_Socketed",
                  "Waveshare RP2040-Zero module (header pins only)")
    left = list(range(1, 12))     # pins 1..11
    right = list(range(12, 24))   # pins 12..23
    h = 2.54 * 12
    s += '    (symbol "%s_0_1"\n      (rectangle (start -10.16 %g) (end 10.16 %g) (stroke (width 0.254) (type default) (color 0 0 0 0)) (fill (type background)))\n    )\n' % (name, 16.51, -16.51)
    s += '    (symbol "%s_1_1"\n' % name
    for i, n in enumerate(left):
        s += _sym_pin(str(n), RP2040_ZERO_PINS[n - 1], -12.7, 15.24 - 2.54 * i, 0)
    for i, n in enumerate(right):
        s += _sym_pin(str(n), RP2040_ZERO_PINS[n - 1], 12.7, 15.24 - 2.54 * i, 180)
    return s + "    )\n  )\n"


def rk10j_symbol(name="RK10J_5pin"):
    s = _sym_head(name, "RV", "10k", "K6TTA:Alps_RK10J_Thumbwheel_5pin",
                  "Alps RK10J thumbwheel potentiometer (single); pins 1,3,5 = end, wiper, end; 2,4 dummy")
    s += ('    (symbol "%s_0_1"\n      (rectangle (start -5.08 7.62) (end 5.08 -7.62) (stroke (width 0.254) (type default) (color 0 0 0 0)) (fill (type background)))\n    )\n' % name)
    s += '    (symbol "%s_1_1"\n' % name
    names = ["END1", "DUMMY", "WIPER", "DUMMY", "END3"]
    for i in range(5):
        s += _sym_pin(str(i + 1), names[i], -7.62, 5.08 - 2.54 * i, 0)
    return s + "    )\n  )\n"


def symbol_lib():
    return ('(kicad_symbol_lib (version 20211014) (generator k6tta_gen)\n' + rp2040_zero_symbol() +
            rk10j_symbol() + ')\n')
