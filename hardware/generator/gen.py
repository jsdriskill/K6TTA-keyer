"""Generate the K6TTA keyer main + front board KiCad projects."""
import json, math, os, re, sys, uuid, copy, csv
from sexpr import parse, dump, Str, find, find1, q
import customlib

KLIB = os.environ.get("KICAD_LIB_DIR", "/usr/share/kicad")  # folder with KiCad 6-era symbols/ and footprints/
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/k6tta-hw"


def U():
    return str(uuid.uuid4())


# ---------------------------------------------------------------- design data
GND, V5, V33 = "GND", "+5V", "+3V3"

# LCSC part numbers: (number, note)
LC = {
    "10k": ("C17414", "0805 basic"), "100k": ("C149504", "0805 basic"), "100": ("C17408", "0805 basic"),
    "120": ("C17437", "0805 basic (confirmed)"), "470": ("C17710", "0805 basic"), "680": ("C17798", "0805 basic (confirmed)"),
    "1n": ("C46653", "0805 50V basic (confirmed)"), "10n": ("C1710", "0805 50V basic (confirmed)"),
    "100n": ("C49678", "0805 50V basic"), "22u": ("C45783", "0805 25V X5R basic (confirmed)"),
    "AO3400A": ("C20917", "basic (confirmed)"), "1N4148W": ("C81598", "SOD-123 basic"),
}

R0805, C0805 = "Resistor_SMD:R_0805_2012Metric", "Capacitor_SMD:C_0805_2012Metric"
JACK = "Connector_Audio:Jack_3.5mm_CUI_SJ1-3525N_Horizontal"


def P(ref, sym, value, fp, pos, pins, lcsc="", mfr="", assembly="JLC", note=""):
    return dict(ref=ref, sym=sym, value=value, fp=fp, pos=pos, pins=pins, lcsc=lcsc, mfr=mfr,
                assembly=assembly, note=note)


def R(ref, val, pos, a, b):
    return P(ref, "Device:R", val, R0805, pos, {"1": a, "2": b}, LC[val][0] if val in LC else "")


def C(ref, val, pos, a, b):
    return P(ref, "Device:C", val + "F" if not val.endswith("F") else val, C0805, pos, {"1": a, "2": b},
             LC[val][0] if val in LC else "")


zero = {str(i + 1): None for i in range(23)}
zero.update({"1": V5, "2": GND, "3": V33, "10": "SCL", "11": "SDA", "12": "MSG3", "13": "MSG2", "14": "MSG1",
             "15": "ENC_SW", "16": "ENC_B", "17": "ENC_A", "18": "SIDETONE", "19": "TX_KEY", "20": "DAH",
             "21": "DIT"})

# main-board 2x8 right-angle socket: odd row = upper/rear row (signals), even row = lower/front row
MAIN_HDR = {"1": "SCL", "3": "SDA", "5": "MSG3", "7": "MSG2", "9": "MSG1", "11": "ENC_SW", "13": "ENC_B",
            "15": "ENC_A", "2": GND, "4": V33}
for n in range(6, 17, 2):
    MAIN_HDR[str(n)] = GND
# front-board header (mounted on the back, rotated 90): front pin 2i+2 = upper row = main pin 2i+1
FRONT_HDR = {}
for i in range(8):
    FRONT_HDR[str(2 * i + 2)] = MAIN_HDR[str(2 * i + 1)]
    FRONT_HDR[str(2 * i + 1)] = MAIN_HDR[str(2 * i + 2)]

MH = "MountingHole:MountingHole_3.2mm_M3"

main_parts = [
    P("U1", "K6TTA:RP2040-Zero", "RP2040-Zero", "K6TTA:RP2040-Zero_Socketed", (128, 111.75, 0), zero,
      assembly="hand", note="Waveshare RP2040-Zero (clone) on 2.54mm female headers 1x9, 1x9, 1x5; USB-C to rear"),
    # paddle jack
    P("J1", "Connector:AudioJack3_SwitchTR", "KEY (paddle)", JACK, (159.5, 140, 90),
      {"T": "DIT", "R": "DAH", "S": GND, "TN": None, "RN": None}, mfr="Same Sky SJ1-3525N", assembly="hand"),
    R("R1", "680", (149.5, 132.5, 0), "DIT", V33),
    C("C1", "1n", (149.5, 136.5, 0), "DIT", GND),
    R("R2", "680", (149.5, 144.5, 0), "DAH", V33),
    C("C2", "1n", (149.5, 148.5, 0), "DAH", GND),
    # rig output
    P("U2", "Isolator:4N35", "4N35", "Package_DIP:DIP-6_W7.62mm", (139, 104, 0),
      {"1": "LED_A", "2": GND, "3": None, "4": "RIG_COM", "5": "RIG_KEY", "6": "OPTO_B"},
      mfr="4N35 DIP-6 (socket optional)", assembly="hand"),
    R("R3", "120", (140.5, 113.5, 0), "TX_KEY", "LED_A"),
    R("R4", "10k", (149.7, 106.5, 90), "OPTO_B", "RIG_COM"),
    P("J2", "Connector:AudioJack3_SwitchTR", "RIG", JACK, (157, 104.5, 180),
      {"T": "RIG_KEY", "S": "RIG_COM", "R": None, "RN": None, "TN": None}, mfr="Same Sky SJ1-3525N",
      assembly="hand"),
    C("C3", "10n", (157.5, 116.5, 0), "RIG_COM", GND),
    C("C4", "10n", (149.7, 111.5, 90), "RIG_KEY", "RIG_COM"),
    # sidetone / headphones / speaker
    R("R5", "470", (116, 146, 0), "SIDETONE", "VOL_IN"),
    P("RV1", "K6TTA:RK10J_5pin", "10k thumbwheel", "K6TTA:Alps_RK10J_Thumbwheel_5pin", (104.5, 148, 90),
      {"1": None, "2": None, "3": "HP", "4": "VOL_IN", "5": "HP"}, lcsc="C470643", mfr="Alps RK10J11E0034",
      assembly="hand", note="Rheostat: pin4 = end, pins 3+5 = wipers under both published pinouts. VERIFY footprint."),
    P("J3", "Connector:AudioJack3_SwitchTR", "PHONES", JACK, (104.5, 133, 270),
      {"T": "HP", "R": "HP", "S": GND, "TN": "HP_SW", "RN": None}, mfr="Same Sky SJ1-3525N", assembly="hand"),
    R("R6", "100", (116.5, 123.5, 90), "HP_SW", "GATE"),
    R("R7", "100k", (116.5, 118.5, 90), "GATE", GND),
    P("Q1", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", (112, 123, 0),
      {"1": "GATE", "2": GND, "3": "SPK_N"}, LC["AO3400A"][0]),
    P("D1", "Diode:1N4148W", "1N4148W", "Diode_SMD:D_SOD-123", (112, 104.5, 0),
      {"1": "SPK_P", "2": "SPK_N"}, LC["1N4148W"][0]),
    P("R8", "Device:R", "22R 1/2W", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
      (106, 117.5, 0), {"1": V5, "2": "SPK_P"}, mfr="22 ohm 0.5W axial (change value to set speaker level)",
      assembly="hand"),
    P("J4", "Connector_Generic:Conn_01x02", "SPEAKER", "Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
      (107.5, 110, 0), {"1": "SPK_P", "2": "SPK_N"}, mfr="JST B2B-XH-A", assembly="hand"),
    C("C5", "22u", (116.5, 104.5, 90), V5, GND),
    C("C6", "22u", (116.5, 108, 90), V5, GND),
    C("C7", "100n", (116.5, 111.5, 90), V5, GND),
    C("C8", "100n", (146.5, 140, 0), V33, GND),
    # board-to-board
    P("J5", "Connector_Generic:Conn_02x08_Odd_Even", "TO FRONT", "Connector_PinSocket_2.54mm:PinSocket_2x08_P2.54mm_Horizontal",
      (123.11, 143.43, 90), MAIN_HDR, mfr="2x8 female socket, right angle, 2.54mm", assembly="hand"),
    P("H1", "Mechanical:MountingHole", "M3", MH, (103.5, 103.5, 0), {}, assembly="none"),
    P("H2", "Mechanical:MountingHole", "M3", MH, (160, 123.5, 0), {}, assembly="none"),
    P("H3", "Mechanical:MountingHole", "M3", MH, (117.5, 152.5, 0), {}, assembly="none"),
    P("H4", "Mechanical:MountingHole", "M3", MH, (159.5, 151.5, 0), {}, assembly="none"),
]

front_parts = [
    P("J1", "Connector_Generic:Conn_02x08_Odd_Even", "TO MAIN", "Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical",
      (129.11, 150, 90), FRONT_HDR, mfr="2x8 male header 2.54mm, straight; MOUNT ON BACK", assembly="hand"),
    P("J2", "Connector_Generic:Conn_01x04", "OLED", "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical",
      (115.84, 102.5, 90), {"1": GND, "2": V33, "3": "SCL", "4": "SDA"},
      mfr="1x4 female header for 0.96in SSD1306 I2C module (GND VCC SCL SDA)", assembly="hand"),
    P("SW1", "Device:RotaryEncoder_Switch", "EC11", "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm",
      (152.5, 110.5, 0), {"A": "ENC_A", "B": "ENC_B", "C": GND, "S1": "ENC_SW", "S2": GND},
      mfr="EC11 with push switch", assembly="hand"),
    P("SW2", "Switch:SW_Push", "MSG1", "Button_Switch_THT:SW_PUSH-12mm", (108.75, 136.5, 0), {"1": "MSG1", "2": GND},
      lcsc="C84931", mfr="Omron B3F-4055 + B32-2000 series cap", assembly="hand"),
    P("SW3", "Switch:SW_Push", "MSG2", "Button_Switch_THT:SW_PUSH-12mm", (131.75, 136.5, 0), {"1": "MSG2", "2": GND},
      lcsc="C84931", mfr="Omron B3F-4055 + B32-2000 series cap", assembly="hand"),
    P("SW4", "Switch:SW_Push", "MSG3", "Button_Switch_THT:SW_PUSH-12mm", (154.75, 136.5, 0), {"1": "MSG3", "2": GND},
      lcsc="C84931", mfr="Omron B3F-4055 + B32-2000 series cap", assembly="hand"),
    P("H1", "Mechanical:MountingHole", "M3", MH, (103.5, 103.5, 0), {}, assembly="none"),
    P("H2", "Mechanical:MountingHole", "M3", MH, (172.5, 103.5, 0), {}, assembly="none"),
    P("H3", "Mechanical:MountingHole", "M3", MH, (103.5, 150.5, 0), {}, assembly="none"),
    P("H4", "Mechanical:MountingHole", "M3", MH, (172.5, 150.5, 0), {}, assembly="none"),
]

BOARDS = {
    "k6tta-main": dict(parts=main_parts, outline=(100, 100, 164, 156), notches=[("T", 157), ("R", 140), ("L", 133)], title="K6TTA Keyer - Main board",
                       texts=[("RIG", 153, 116, "F.SilkS"), ("KEY", 154, 131.5, "F.SilkS"),
                              ("PHONES", 106, 125, "F.SilkS"), ("VOL", 113.5, 155, "F.SilkS"),
                              ("USB", 128, 101.3, "F.SilkS"),
                              ("TO FRONT BOARD", 132, 140.5, "F.SilkS"),
                              ("K6TTA keyer main v0.1", 132, 128, "F.SilkS")],
                       drawings=[]),
    "k6tta-front": dict(parts=front_parts, outline=(100, 100, 176, 154), notches=[], title="K6TTA Keyer - Front board",
                        texts=[("J1 MOUNTS ON BACK", 138, 153, "B.SilkS"), ("K6TTA keyer front v0.1", 120, 131, "F.SilkS"),
                               ("1", 115, 128, "F.SilkS"), ("2", 138, 128, "F.SilkS"), ("3", 161, 128, "F.SilkS")],
                        drawings=[("OLED module 27.3 x 27.8 (check yours)", (106, 101, 133.3, 128.8))]),
}

# ---------------------------------------------------------------- symbols
_symcache = {}


def lib_symbol(lib_id):
    """Return (sexpr list for lib_symbols with full lib_id name, list of pins (num, x, y, angle, type))."""
    if lib_id in _symcache:
        return _symcache[lib_id]
    lib, name = lib_id.split(":")
    if lib == "K6TTA":
        text = customlib.symbol_lib()
    else:
        text = open(os.path.join(KLIB, "symbols", lib + ".kicad_sym")).read()
    tree = parse(text)
    syms = {s[1]: s for s in find(tree, "symbol")}
    s = copy.deepcopy(syms[name])
    ext = find1(s, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        pname = ext[1]
        # child properties override parent ones
        childprops = {p[1]: p for p in find(s, "property")}
        new = [parent[0], Str(name)]
        for item in parent[2:]:
            if isinstance(item, list) and item[0] == "property" and item[1] in childprops:
                new.append(childprops.pop(item[1]))
            elif isinstance(item, list) and item[0] == "symbol":
                item[1] = Str(item[1].replace(pname + "_", name + "_", 1))
                new.append(item)
            else:
                new.append(item)
        for p in childprops.values():
            new.append(p)
        s = new
    s[1] = Str(lib_id)
    pins = []
    for sub in find(s, "symbol"):
        m = re.match(r".*_(\d+)_(\d+)$", sub[1])
        if m and m.group(2) == "2":
            continue  # De Morgan alternate
        for p in find(sub, "pin"):
            at = find1(p, "at")
            num = find1(p, "number")[1]
            pins.append((str(num), float(at[1]), float(at[2]), int(float(at[3])), p[1]))
    _symcache[lib_id] = (s, pins)
    return s, pins


# ---------------------------------------------------------------- schematic
def label(net, x, y, ang):
    just = "left" if ang in (0, 90) else "right"
    return ["label", Str(net), ["at", x, y, ang],
            ["effects", ["font", ["size", 1.27, 1.27]], ["justify", just, "bottom"]], ["uuid", U()]]


def schematic(board, parts, sym_uuid, title):
    items = []
    used = []
    for p in parts:
        if p["sym"] not in used:
            used.append(p["sym"])
    libsyms = ["lib_symbols"] + [copy.deepcopy(lib_symbol(l)[0]) for l in used]

    # flow layout
    x0, y0, maxw = 25.4, 30.48, 380
    x, y, rowh = x0, y0, 0
    insts = []
    for p in parts:
        s, pins = lib_symbol(p["sym"])
        if pins:
            xs = [pp[1] for pp in pins]
            ys = [-pp[2] for pp in pins]
            minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        else:
            minx = maxx = miny = maxy = 0
        minx -= 22; maxx += 22; miny -= 8; maxy += 8
        w, h = maxx - minx, maxy - miny
        if x + w > maxw:
            x, y, rowh = x0, y + rowh + 7.62, 0
        sx = round((x - minx) / 2.54) * 2.54
        sy = round((y - miny) / 2.54) * 2.54
        x += w + 5.08
        rowh = max(rowh, h)
        uid = sym_uuid[p["ref"]]
        props = [
            ["property", Str("Reference"), Str(p["ref"]), ["id", 0], ["at", sx, sy + miny + 3, 0],
             ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", Str("Value"), Str(p["value"]), ["id", 1], ["at", sx, sy + maxy - 3, 0],
             ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["property", Str("Footprint"), Str(p["fp"]), ["id", 2], ["at", sx, sy, 0],
             ["effects", ["font", ["size", 1.27, 1.27]], "hide"]],
            ["property", Str("Datasheet"), Str("~"), ["id", 3], ["at", sx, sy, 0],
             ["effects", ["font", ["size", 1.27, 1.27]], "hide"]],
        ]
        fid = 4
        for key in ("lcsc", "mfr"):
            if p[key]:
                props.append(["property", Str("LCSC" if key == "lcsc" else "MPN/Notes"), Str(p[key]), ["id", fid],
                              ["at", sx, sy, 0], ["effects", ["font", ["size", 1.27, 1.27]], "hide"]])
                fid += 1
        sym = ["symbol", ["lib_id", Str(p["sym"])], ["at", sx, sy, 0], ["unit", 1],
               ["in_bom", "no" if p["assembly"] == "none" else "yes"], ["on_board", "yes"], ["uuid", uid]] + props
        for (num, px, py, ang, ptype) in pins:
            sym.append(["pin", Str(num), ["uuid", U()]])
        items.append(sym)
        insts.append(["path", Str("/" + uid), ["reference", Str(p["ref"])], ["unit", 1], ["value", Str(p["value"])],
                      ["footprint", Str(p["fp"])]])
        # labels / no-connects at every pin end
        for (num, px, py, ang, ptype) in pins:
            ax, ay = round(sx + px, 3), round(sy - py, 3)
            if ptype == "no_connect":
                continue
            net = p["pins"].get(num)
            if net:
                items.append(label(net, ax, ay, (ang + 180) % 360))
            else:
                items.append(["no_connect", ["at", ax, ay], ["uuid", U()]])
    # notes
    notes = {
        "k6tta-main": ["Generated from K6TTA-keyer config.h pin map. Labels connect by name.",
                       "J5 is a 2x8 RIGHT-ANGLE socket at the front edge; odd row (rear/upper) = signals, even row = GND/3V3.",
                       "RV1: Alps RK10J 5-pin thumbwheel used as a rheostat (pin 4 = end, pins 3+5 = wipers). Verify pinout.",
                       "C3 = RF fix (rig jack sleeve to keyer GND). C4 optional (across rig tip/sleeve)."],
        "k6tta-front": ["J1 is a straight 2x8 header soldered on the BACK of this board; it plugs into J5 on the main board.",
                        "Front J1 pin 2i+2 (upper row) mates with main J5 pin 2i+1; pin 2i+1 (lower row) mates with main pin 2i+2.",
                        "OLED module pin order: GND VCC SCL SDA (check your module)."],
    }[board]
    ny = 285
    for t in reversed(notes):
        items.append(["text", Str(t), ["at", 20, ny, 0], ["effects", ["font", ["size", 1.5, 1.5]], ["justify", "left", "bottom"]],
                      ["uuid", U()]])
        ny -= 4
    paper = "A3" if y + rowh < 270 else "A2"
    root = ["kicad_sch", ["version", 20211123], ["generator", "eeschema"], ["uuid", U()], ["paper", Str(paper)],
            ["title_block", ["title", Str(title)], ["rev", Str("0.1")], ["comment", 1, Str("Generated draft - review before ordering")]],
            libsyms] + items + [["sheet_instances", ["path", Str("/"), ["page", Str("1")]]],
                                ["symbol_instances"] + insts]
    return dump(root) + "\n"


# ---------------------------------------------------------------- PCB
def load_fp(fpid):
    lib, name = fpid.split(":")
    if lib == "K6TTA":
        text = {"RP2040-Zero_Socketed": customlib.rp2040_zero_footprint,
                "Alps_RK10J_Thumbwheel_5pin": customlib.rk10j_footprint}[name]()
    else:
        text = open(os.path.join(KLIB, "footprints", lib + ".pretty", name + ".kicad_mod")).read()
    return parse(text)


def xform(x, y, X, Y, rot):
    t = math.radians(rot)
    return X + x * math.cos(t) + y * math.sin(t), Y - x * math.sin(t) + y * math.cos(t)


def retstamp(e):
    if isinstance(e, list):
        if e and e[0] == "tstamp":
            e[1] = U()
        for x in e:
            retstamp(x)


def footprint(p, netidx, uid, sheetfile):
    fp = load_fp(p["fp"])
    X, Y, rot = p["pos"]
    out = ["footprint", Str(p["fp"])]
    rest = []
    for item in fp[2:]:
        if isinstance(item, list) and item[0] in ("version", "generator"):
            continue
        if isinstance(item, list) and item[0] in ("fp_line", "fp_arc", "fp_circle", "fp_rect", "fp_poly"):
            lay = find1(item, "layer")
            if lay and lay[1] == "Edge.Cuts":
                continue
        if isinstance(item, list) and item[0] == "fp_text":
            if item[1] == "reference":
                item[2] = Str(p["ref"])
            elif item[1] == "value":
                item[2] = Str(p["value"])
            at = find1(item, "at")
            a = (float(at[3]) if len(at) > 3 and at[3] not in ("unlocked",) else 0) + rot
            at[:] = ["at", at[1], at[2]] + ([round(a % 360, 3)] if a % 360 else [])
        if isinstance(item, list) and item[0] == "pad":
            at = find1(item, "at")
            a = (float(at[3]) if len(at) > 3 else 0) + rot
            at[:] = ["at", at[1], at[2]] + ([round(a % 360, 3)] if a % 360 else [])
            net = p["pins"].get(str(item[1]))
            if net:
                pos = next(i for i, x in enumerate(item) if isinstance(x, list) and x[0] == "layers") + 1
                item.insert(pos, ["net", netidx[net], Str("/" + net)])
        if isinstance(item, list) and item[0] == "model":
            m = str(item[1]).replace("${KICAD6_3DMODEL_DIR}", "${KICAD10_3DMODEL_DIR}").replace(".wrl", ".step")
            item[1] = Str(m)
        rest.append(item)
    layer = find1(rest, "layer")
    rest.remove(layer)
    head = [layer, ["tstamp", uid], ["at", X, Y] + ([rot] if rot else [])]
    # BOM attribute follows the symbol; copy symbol fields onto the footprint
    for a in find(rest, "attr"):
        a[:] = [x for x in a if x != "exclude_from_bom"]
        if p["assembly"] == "none":
            a.append("exclude_from_bom")
    extra = [["property", Str(k), Str(p[f])] for k, f in (("LCSC", "lcsc"), ("MPN/Notes", "mfr")) if p[f]]
    props = extra + [["property", Str("Sheetfile"), Str(sheetfile)], ["property", Str("Sheetname"), Str("")],
             ["path", Str("/" + uid)]]
    out += head + props + rest
    retstamp(out[3:])
    return out


LAYERS = ["layers", [0, Str("F.Cu"), "signal"], [31, Str("B.Cu"), "signal"],
          [32, Str("B.Adhes"), "user", Str("B.Adhesive")], [33, Str("F.Adhes"), "user", Str("F.Adhesive")],
          [34, Str("B.Paste"), "user"], [35, Str("F.Paste"), "user"],
          [36, Str("B.SilkS"), "user", Str("B.Silkscreen")], [37, Str("F.SilkS"), "user", Str("F.Silkscreen")],
          [38, Str("B.Mask"), "user"], [39, Str("F.Mask"), "user"],
          [40, Str("Dwgs.User"), "user", Str("User.Drawings")], [41, Str("Cmts.User"), "user", Str("User.Comments")],
          [42, Str("Eco1.User"), "user", Str("User.Eco1")], [43, Str("Eco2.User"), "user", Str("User.Eco2")],
          [44, Str("Edge.Cuts"), "user"], [45, Str("Margin"), "user"],
          [46, Str("B.CrtYd"), "user", Str("B.Courtyard")], [47, Str("F.CrtYd"), "user", Str("F.Courtyard")],
          [48, Str("B.Fab"), "user"], [49, Str("F.Fab"), "user"]]


def gr_text(t, x, y, layer, size=1.0):
    eff = ["effects", ["font", ["size", size, size], ["thickness", 0.15]]]
    if layer.startswith("B."):
        eff.append(["justify", "mirror"])
    return ["gr_text", Str(t), ["at", x, y], ["layer", Str(layer)], ["tstamp", U()], eff]


def pcb(parts, sym_uuid, sheetfile, outline, texts, drawings, notches=()):
    nets = sorted({n for p in parts for n in p["pins"].values() if n})
    netidx = {n: i + 1 for i, n in enumerate(nets)}
    root = ["kicad_pcb", ["version", 20211014], ["generator", "pcbnew"], ["general", ["thickness", 1.6]],
            ["paper", Str("A4")], copy.deepcopy(LAYERS), ["setup", ["pad_to_mask_clearance", 0]],
            ["net", 0, Str("")]] + [["net", netidx[n], Str("/" + n)] for n in nets]
    fps = []
    for p in parts:
        f = footprint(p, netidx, sym_uuid[p["ref"]], sheetfile)
        root.append(f)
        fps.append((p, f))
    x1, y1, x2, y2 = outline
    pts = [(x1, y1)]
    for side, c in sorted([n for n in notches if n[0] == "T"], key=lambda n: n[1]):
        pts += [(c - 2.2, y1), (c - 2.2, y1 + 1.4), (c + 2.2, y1 + 1.4), (c + 2.2, y1)]
    pts += [(x2, y1)]
    for side, c in sorted([n for n in notches if n[0] == "R"], key=lambda n: n[1]):
        pts += [(x2, c - 2.2), (x2 - 1.4, c - 2.2), (x2 - 1.4, c + 2.2), (x2, c + 2.2)]
    pts += [(x2, y2), (x1, y2)]
    for side, c in sorted([n for n in notches if n[0] == "L"], key=lambda n: -n[1]):
        pts += [(x1, c + 2.2), (x1 + 1.4, c + 2.2), (x1 + 1.4, c - 2.2), (x1, c - 2.2)]
    segs = list(zip(pts, pts[1:] + pts[:1]))
    for a, b in segs:
        root.append(["gr_line", ["start", a[0], a[1]], ["end", b[0], b[1]], ["layer", Str("Edge.Cuts")],
                     ["width", 0.1], ["tstamp", U()]])
    for t, x, y, layer in texts:
        root.append(gr_text(t, x, y, layer))
    for t, (a, b, c, d) in drawings:
        for s, e in [((a, b), (c, b)), ((c, b), (c, d)), ((c, d), (a, d)), ((a, d), (a, b))]:
            root.append(["gr_line", ["start", s[0], s[1]], ["end", e[0], e[1]], ["layer", Str("Dwgs.User")],
                         ["width", 0.1], ["tstamp", U()]])
        root.append(gr_text(t, (a + c) / 2, d - 1.5, "Dwgs.User", 0.8))
    return dump(root) + "\n", fps, netidx


# ---------------------------------------------------------------- geometry helpers for checks / preview
def fp_geometry(p, f):
    X, Y, rot = p["pos"]
    pads, crt = [], []
    for item in f:
        if isinstance(item, list) and item[0] == "pad":
            at = find1(item, "at")
            size = find1(item, "size")
            gx, gy = xform(float(at[1]), float(at[2]), X, Y, rot)
            net = find1(item, "net")
            a = float(at[3]) if len(at) > 3 else 0
            sx, sy = float(size[1]), float(size[2])
            if round(a) % 180 == 90:
                sx, sy = sy, sx
            pads.append((str(item[1]), gx, gy, sx, sy, net[2] if net else None, item[3]))
        if isinstance(item, list) and item[0] in ("fp_line",):
            lay = find1(item, "layer")
            if lay[1] == "F.CrtYd":
                s, e = find1(item, "start"), find1(item, "end")
                crt.append(xform(float(s[1]), float(s[2]), X, Y, rot))
                crt.append(xform(float(e[1]), float(e[2]), X, Y, rot))
        if isinstance(item, list) and item[0] == "fp_circle":
            lay = find1(item, "layer")
            if lay[1] == "F.CrtYd":
                c, e = find1(item, "center"), find1(item, "end")
                r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                cx, cy = xform(float(c[1]), float(c[2]), X, Y, rot)
                crt += [(cx - r, cy - r), (cx + r, cy + r)]
    bbox = None
    if crt:
        xs, ys = [c[0] for c in crt], [c[1] for c in crt]
        bbox = (min(xs), min(ys), max(xs), max(ys))
    return pads, bbox


def project_file(name):
    return json.dumps({"board": {"design_settings": {}}, "meta": {"filename": name + ".kicad_pro", "version": 1},
                       "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
                       "sheets": [], "text_variables": {}}, indent=2) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for board, cfg in BOARDS.items():
        d = os.path.join(OUT, board)
        os.makedirs(os.path.join(d, "lib", "K6TTA.pretty"), exist_ok=True)
        open(os.path.join(d, "lib", "K6TTA.pretty", "RP2040-Zero_Socketed.kicad_mod"), "w").write(customlib.rp2040_zero_footprint())
        open(os.path.join(d, "lib", "K6TTA.pretty", "Alps_RK10J_Thumbwheel_5pin.kicad_mod"), "w").write(customlib.rk10j_footprint())
        open(os.path.join(d, "lib", "K6TTA.kicad_sym"), "w").write(customlib.symbol_lib())
        open(os.path.join(d, "sym-lib-table"), "w").write(
            '(sym_lib_table\n  (version 7)\n  (lib (name "K6TTA")(type "KiCad")(uri "${KIPRJMOD}/lib/K6TTA.kicad_sym")(options "")(descr "K6TTA keyer parts"))\n)\n')
        open(os.path.join(d, "fp-lib-table"), "w").write(
            '(fp_lib_table\n  (version 7)\n  (lib (name "K6TTA")(type "KiCad")(uri "${KIPRJMOD}/lib/K6TTA.pretty")(options "")(descr "K6TTA keyer footprints"))\n)\n')
        parts = cfg["parts"]
        sym_uuid = {p["ref"]: U() for p in parts}
        sch = schematic(board, parts, sym_uuid, cfg["title"])
        open(os.path.join(d, board + ".kicad_sch"), "w").write(sch)
        brd, fps, netidx = pcb(parts, sym_uuid, board + ".kicad_sch", cfg["outline"], cfg["texts"], cfg["drawings"], cfg["notches"])
        open(os.path.join(d, board + ".kicad_pcb"), "w").write(brd)
        open(os.path.join(d, board + ".kicad_pro"), "w").write(project_file(board))
        report[board] = dict(fps=fps, netidx=netidx, cfg=cfg)
    return report


if __name__ == "__main__":
    main()
