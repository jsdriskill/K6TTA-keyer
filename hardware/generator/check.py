"""Checks + previews for the generated boards: courtyard overlaps, pads off-board, schematic/PCB net match."""
import sys, math, itertools, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import gen
from sexpr import parse, find, find1

OUT = sys.argv[1]
PRE = sys.argv[2]
rep = gen.main()  # regenerate (same data) and get geometry
problems = []
for board, r in rep.items():
    cfg = r["cfg"]
    x1, y1, x2, y2 = cfg["outline"]
    geo = [(p, *gen.fp_geometry(p, f)) for p, f in r["fps"]]
    # courtyard overlaps
    for (pa, _, ba), (pb, _, bb) in itertools.combinations(geo, 2):
        if ba and bb and ba[0] < bb[2] and bb[0] < ba[2] and ba[1] < bb[3] and bb[1] < ba[3]:
            ov = (min(ba[2], bb[2]) - max(ba[0], bb[0])) * (min(ba[3], bb[3]) - max(ba[1], bb[1]))
            if ov > 0.05:
                problems.append("%s: courtyard overlap %s / %s (%.1f mm2)" % (board, pa["ref"], pb["ref"], ov))
    # pads must be inside the board (with 0.3 mm margin)
    for p, pads, bb in geo:
        for (num, gx, gy, sx, sy, net, kind) in pads:
            if gx - sx / 2 < x1 + 0.5 or gx + sx / 2 > x2 - 0.5 or gy - sy / 2 < y1 + 0.5 or gy + sy / 2 > y2 - 0.5:
                problems.append("%s: pad %s.%s near/over board edge at (%.2f, %.2f)" % (board, p["ref"], num, gx, gy))
    # pad-to-pad spacing between different nets / parts
    allpads = [(p["ref"], *pd) for p, pads, _ in geo for pd in pads]
    for a, b in itertools.combinations(allpads, 2):
        if a[0] == b[0]:
            continue
        dx = abs(a[2] - b[2]) - (a[4] + b[4]) / 2
        dy = abs(a[3] - b[3]) - (a[5] + b[5]) / 2
        gap = max(dx, dy)
        if gap < 0.3:
            problems.append("%s: pads %s.%s and %s.%s only %.2f mm apart" % (board, a[0], a[1], b[0], b[1], gap))

    # schematic: every labelled pin end must carry the PCB pad's net
    sch = parse(open(os.path.join(OUT, board, board + ".kicad_sch")).read())
    labels = {}
    for l in find(sch, "label"):
        at = find1(l, "at")
        labels[(round(float(at[1]), 2), round(float(at[2]), 2))] = str(l[1])
    ncs = {(round(float(find1(n, "at")[1]), 2), round(float(find1(n, "at")[2]), 2)) for n in find(sch, "no_connect")}
    for s in find(sch, "symbol"):
        lib = str(find1(s, "lib_id")[1])
        at = find1(s, "at")
        sx, sy = float(at[1]), float(at[2])
        ref = [str(p[2]) for p in find(s, "property") if p[1] == "Reference"][0]
        part = next(p for p in cfg["parts"] if p["ref"] == ref)
        _, pins = gen.lib_symbol(lib)
        for (num, px, py, ang, ptype) in pins:
            key = (round(sx + px, 2), round(sy - py, 2))
            want = part["pins"].get(num)
            got = labels.get(key)
            if ptype == "no_connect":
                continue
            if want and got != want:
                problems.append("%s: %s pin %s label %r != %r" % (board, ref, num, got, want))
            if not want and key not in ncs:
                problems.append("%s: %s pin %s has no no-connect" % (board, ref, num))
        # every footprint pad number should exist as a symbol pin (except mechanical)
        fpnums = {pd[0] for p, pads, _ in geo if p["ref"] == ref for pd in pads if pd[0] not in ("", "MP")}
        symnums = {pn[0] for pn in pins}
        if fpnums - symnums:
            problems.append("%s: %s footprint pads without symbol pins: %s" % (board, ref, sorted(fpnums - symnums)))
        if symnums - fpnums - {pn[0] for pn in pins if pn[4] == "no_connect"}:
            problems.append("%s: %s symbol pins without pads: %s" % (board, ref, sorted(symnums - fpnums)))

    # preview
    fig, ax = plt.subplots(figsize=(10, 10 * (y2 - y1) / (x2 - x1) + 0.6))
    ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, lw=2, color="k"))
    colors = {}
    cmap = plt.get_cmap("tab20")
    for p, pads, bb in geo:
        if bb:
            ax.add_patch(Rectangle((bb[0], bb[1]), bb[2] - bb[0], bb[3] - bb[1], fill=False, ls="--", lw=0.7, color="gray"))
            ax.text((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, p["ref"], ha="center", va="center", fontsize=8,
                    color="navy", weight="bold")
        for (num, gx, gy, sx, sy, net, kind) in pads:
            c = "lightgray" if not net else colors.setdefault(net, cmap(len(colors) % 20))
            ax.add_patch(Rectangle((gx - sx / 2, gy - sy / 2), sx, sy, color=c, ec="k", lw=0.3))
    # ratsnest (chain each net's pads by nearest neighbour)
    bynet = {}
    for p, pads, _ in geo:
        for pd in pads:
            if pd[5]:
                bynet.setdefault(pd[5], []).append((pd[1], pd[2]))
    for net, pts in bynet.items():
        done = [pts[0]]
        rest = pts[1:]
        while rest:
            a, b = min(((a, b) for a in done for b in rest), key=lambda ab: math.dist(*ab))
            ax.plot([a[0], b[0]], [a[1], b[1]], lw=0.5, color=colors.get(net, "k"), alpha=0.8)
            done.append(b); rest.remove(b)
    for t, x, y, layer in cfg["texts"]:
        ax.text(x, y, t, fontsize=6, ha="center", va="center", color="green" if layer.startswith("F") else "purple")
    ax.set_xlim(x1 - 6, x2 + 6); ax.set_ylim(y2 + 6, y1 - 6); ax.set_aspect("equal")
    ax.set_title(cfg["title"] + " (top view; dashed = courtyards, lines = ratsnest)")
    fig.tight_layout()
    fig.savefig(os.path.join(PRE, board + "-preview.png"), dpi=130)
print("\n".join(problems) if problems else "no problems found")
