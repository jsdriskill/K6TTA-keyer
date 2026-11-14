# K6TTA keyer enclosure (draft v0.1)

Two-piece printed case, loosely after the CRT iMac G3: a wide rounded front that narrows to a straight body, a top that
slopes down to the back, and rounded corners everywhere. Parametric OpenSCAD source: `k6tta-enclosure.scad`.

* **Base** (`part="base"`): front panel, floor and rear wall. Includes the 1/4" radio lip under the front edge, four magnet
  pockets underneath, the main-board standoffs and the front-board bosses.
* **Cover** (`part="cover"`): top and sides. Includes the speaker ring with snap catches, the grille, the side jack
  openings and the thumbwheel scallop.

Outside size: 88 mm wide at the front (76 mm from 18 mm back), 74 mm deep, 70 mm tall at the front and 48 mm at the rear,
top sloping about 21 degrees. The lip adds 6.35 mm below the bottom at the front.

## Render the STLs

```
sudo pacman -S openscad
openscad -o base.stl  -D 'part="base"'  k6tta-enclosure.scad
openscad -o cover.stl -D 'part="cover"' k6tta-enclosure.scad
```

Open the file in OpenSCAD with `part = "assembly"` (the default) to see both halves with the boards ghosted in.
The labels use Liberation Sans Bold (`ttf-liberation`); OpenSCAD substitutes another font if it isn't installed.

`section-x0.png` is a cross-section through the middle from the fit check (boards in green, speaker ring in red).

## Hardware

* 12 x M3 x 8 mm screws, self-tapping into 2.6 mm printed pilots: 4 hold the main board, 4 hold the front board to the
  front panel, 4 come up through the floor to join the halves (heads sit in counterbores so the bottom stays flat).
  Change `pilot_d` if the screws are too tight (2.7) or too loose (2.5). Don't overtighten; the threads are plastic.
* 4 x 10 x 3 mm neodymium disc magnets, glued into the pockets under the floor (`mag_d`, `mag_h`).
* Speaker: 36 mm round, about 5 mm thick at the rim, snapped into the ring under the grille (`spk_d`, `spk_h`).

## Assumptions to check

| Parameter | Value | Why it matters |
|---|---|---|
| OLED mounting | soldered directly to J2 (no socket) | `gap_front` = 6.5 mm sets the front board 6.5 mm behind the panel so the encoder bushing passes through the panel and the button caps stick out. A socket would raise the OLED about 8.5 mm. |
| `sock_row_z` | 1.27 mm | Height of the right-angle socket's lower row above the main board; sets the front board's height. Measure your socket. |
| `jack_z` | 2.6 mm | 3.5 mm jack centre above the main board (side and rear holes are 11 mm so the plug body enters the wall). |
| `wheel_z` | 2.5 mm | Thumbwheel height for the scallop on the left side. |
| `usb_z` | 13.6 mm | USB-C height with the RP2040-Zero on 8.5 mm sockets. |
| `oled_win`, `oled_dz` | 23 x 12 mm, 12 mm below the module top | Display window; compare with your module's glass. |
| `btn_hole` | 12.6 mm | For about 12 mm round caps on the B3F-4055 buttons. |
| Encoder | EC11 with an M7 bushing, ~20 mm shaft | The bushing passes through a 7.4 mm hole; the nut can clamp the panel. |

Board positions come straight from the routed KiCad files (front board holes, buttons at x 115/138/161, encoder shaft at
153,115; main board holes, jacks, thumbwheel and USB-C).

## Printing

* **Cover:** stand it on its rear edge (the flat rear opening). The sloped top and grille then print without supports.
* **Base:** print it floor-down with supports under the floor only. The radio lip hangs 6.35 mm below the floor, so
  the floor needs that much support; the front panel and rear wall print upright with clean holes and labels.
* PETG or PLA, 0.2 mm layers, 3 to 4 walls so the screw pilots have solid plastic around them.

## Assembly

1. Glue the magnets into the base (check polarity matches whatever they stick to).
2. Screw the front board to the four bosses behind the front panel (component side toward the panel).
3. Screw the main board to the four standoffs, sliding its right-angle socket onto the front board's header.
4. Snap the speaker into the ring under the cover's grille and plug it into J4.
5. Lower the cover over the base (the rim on the floor locates it) and fit the four screws from underneath.
