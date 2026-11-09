"""Write netlist checklists, BOMs and a README next to the generated projects."""
import csv, os, sys
import gen

OUT = sys.argv[1]

for board, cfg in gen.BOARDS.items():
    d = os.path.join(OUT, board)
    nets = {}
    for p in cfg["parts"]:
        for pin, net in p["pins"].items():
            if net:
                nets.setdefault(net, []).append("%s.%s" % (p["ref"], pin))
    with open(os.path.join(d, board + "-netlist.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Net", "Pins"])
        for n in sorted(nets):
            w.writerow([n, " ".join(sorted(nets[n], key=lambda s: (s.split(".")[0], s.split(".")[1].zfill(3))))])
    # full BOM grouped by value+footprint+assembly
    groups = {}
    for p in cfg["parts"]:
        if p["assembly"] == "none":
            continue
        k = (p["value"], p["fp"], p["lcsc"], p["mfr"], p["assembly"], p["note"])
        groups.setdefault(k, []).append(p["ref"])
    with open(os.path.join(d, board + "-bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Qty", "Designators", "Value", "Footprint", "LCSC", "JLC class", "Part / notes", "Who solders"])
        cls = {v[0]: v[1] for v in gen.LC.values()}
        for k, refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            val, fp, lc, mfr, asm, note = k
            w.writerow([len(refs), " ".join(refs), val, fp.split(":")[1], lc, cls.get(lc, ""), "; ".join(x for x in (mfr, note) if x),
                        "JLCPCB" if asm == "JLC" else "you"])
    jlc = [(k, refs) for k, refs in groups.items() if k[4] == "JLC"]
    if jlc:
        with open(os.path.join(d, board + "-jlcpcb-bom.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
            for k, refs in sorted(jlc, key=lambda kv: kv[1][0]):
                w.writerow([k[0], ",".join(refs), k[1].split(":")[1], k[2]])

open(os.path.join(OUT, "README.md"), "w").write("""# K6TTA keyer hardware (generated draft v0.1)

Two KiCad projects, written as KiCad 6 files; KiCad 10 opens and upgrades them (save once after opening).

* `k6tta-main/` main board, 64 x 56 mm: RP2040-Zero on sockets (USB-C to the rear), rig jack rear-right,
  paddle jack front-right, headphone jack left with the thumbwheel in front of it, 2x8 right-angle socket on the front edge.
* `k6tta-front/` front board, 76 x 54 mm: 0.96in SSD1306 OLED (on a 1x4 socket), EC11 encoder, three 12 mm message buttons,
  2x8 straight header soldered on the BACK so it plugs into the main board's right-angle socket.

Pin assignments come from `config.h` in K6TTA-keyer (GP2 dit, GP3 dah, GP4 TX key, GP5 sidetone, GP6-8 encoder,
GP9-11 message buttons, GP12/13 I2C).

## Status: parts placed, not routed

1. Open each `.kicad_pro`. If KiCad asks to upgrade or remap anything, accept.
2. In the PCB editor run DRC first (unrouted connections are expected), then route, add a GND pour on both layers, and run DRC again.
3. Optional: Tools > Update Footprints from Library to swap in your installed library copies (same names).
4. 3D models point at `${KICAD10_3DMODEL_DIR}/....step`; if they don't show, check that variable in Preferences > Configure Paths.

## Check before ordering

* **RP2040-Zero pinout** (custom footprint `K6TTA:RP2040-Zero_Socketed`): pin 1 = 5V top-left with USB-C up,
  GP0 top-right, GP9..GP13 on the short row opposite the USB (GP13 at the left). Compare with your clone.
* **Thumbwheel RV1** (`K6TTA:Alps_RK10J_Thumbwheel_5pin`): geometry is from a third-party footprint and is not verified
  against the Alps drawing. Two published pinouts disagree, so it is wired to work with either: pin 4 = one end,
  pins 3 and 5 = wipers (tied), pins 1-2 unused. Check the footprint against the RK10J11E0034 datasheet.
* **Board-to-board header**: main J5 odd pins (rear row of the right-angle socket, upper opening) carry the signals;
  front J1 even pins (upper row) mate with them. Check the height of the socket openings against where the front board sits.
* **OLED module**: pin order GND VCC SCL SDA; module outline is drawn on User.Drawings only (no mounting holes).
* **LCSC numbers**: all JLCPCB-placed parts are chosen from the Basic library (the "JLC class" column says which were confirmed); re-check stock when you order.
* R8 (speaker series resistor) is a 1/2 W axial part you solder, so you can change the speaker level.
""")
print("docs written")
