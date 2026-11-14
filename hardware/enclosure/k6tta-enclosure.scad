// K6TTA keyer enclosure - two-piece, iMac G3 inspired
// Piece A ("base"): front panel + floor + rear wall, with the radio lip and magnet pockets.
// Piece B ("cover"): top + sides, with the speaker mount and grille.
//
// Render one part at a time:
//   openscad -o base.stl  -D 'part="base"'  k6tta-enclosure.scad
//   openscad -o cover.stl -D 'part="cover"' k6tta-enclosure.scad
//   openscad -o preview.png -D 'part="assembly"' k6tta-enclosure.scad
//
// Coordinates: X to the right (seen from the front), Y toward the rear, Z up.
// Y = 0 is the front face, Z = 0 the bottom (the face that sits on the radio).
// All screws: M3 x 8 mm, self-tapping into the printed pilot holes.

part = "assembly";      // "base" | "cover" | "assembly" | "boards"

/* [Shell] */
R          = 8;         // corner radius of the top and vertical edges
Rb         = 4;         // radius of the bottom edges (keeps the bottom flat out to the screw heads)
wall       = 2.5;       // side, top, front and rear wall thickness
floor_t    = 4;         // floor thickness (magnet pockets are recessed into it)
D          = 74;        // overall depth (front face to rear face)
W_front    = 88;        // width at the front
H_front    = 70;        // height at the front
W_rear     = 76;        // width from Y_taper to the rear
H_rear     = 48;        // height at the rear
Y_taper    = 18;        // the sides narrow from W_front to W_rear between Y=R and here

/* [Radio lip] */
lip_drop   = 6.35;      // 1/4" below the bottom
lip_t      = 2.5;       // front-to-back thickness of the lip
lip_r      = 2;         // rounding of the lip's lower corners

/* [Screws] */
pilot_d    = 2.6;       // self-tap pilot for M3 in PETG/PLA (2.5 for softer, 2.7 for harder)
clear_d    = 3.4;       // M3 clearance
head_d     = 6.0;       // counterbore for M3 button head (5.7 mm)
head_h     = 2.0;       // counterbore depth in the floor
boss_d     = 6.4;

/* [Magnets] */
mag_d      = 10.2;      // 10 x 3 mm disc + clearance
mag_h      = 3.2;
mag_pos    = [[-22, 7], [22, 7], [-20, 66], [20, 66]];

/* [Board stack] (from the KiCad files) */
gap_front  = 6.5;       // front board face to front panel inner face (OLED soldered directly)
pcb_t      = 1.6;
hdr_spacer = 2.5;       // plastic spacer of the 2x8 male header
standoff   = 5;         // main board standoff height above the floor
sock_row_z = 1.27;      // lower row of the right-angle socket above the main board (MEASURE)
jack_z     = 2.6;       // 3.5 mm jack centre above the main board
wheel_z    = 2.5;       // thumbwheel mid-plane above the main board
usb_z      = 13.6;      // USB-C centre above the main board (8.5 socket + 2.5 spacer + 1 PCB + 1.6)

/* [Front panel] */
oled_win   = [23, 12];  // visible window (active area of a 0.96" SSD1306 + margin)
oled_dz    = 12.0;      // window centre below the top edge of the OLED module
enc_hole   = 7.4;       // EC11 M7 bushing
btn_hole   = 12.6;      // for ~12 mm round button caps
label_d    = 0.6;       // deboss depth of labels
font       = "Liberation Sans:style=Bold";

/* [Speaker] */
spk_d      = 36;        // speaker diameter
spk_h      = 5;         // speaker thickness at the rim (ring height = spk_h + 1.2)
spk_y      = 44;        // speaker centre (Y) on the sloped top
grille_r   = 14;        // radius of the hole pattern
grille_hole= 2.2;

$fn = 48;

// ---------------------------------------------------------------- derived
slope    = (H_front - H_rear) / ((D - R) - R);
tilt     = atan(slope);                       // top surface angle
function top_z(y) = H_front - slope * (y - R);

fb_front = wall + gap_front;                  // Y of the front board's front face
fb_back  = fb_front + pcb_t;
mb_front = fb_back + hdr_spacer;              // Y of the main board's front edge
mb_bot   = floor_t + standoff;
mb_top   = mb_bot + pcb_t;
fb_bot   = mb_top + sock_row_z - 4.0;         // header lower row is 4 mm above the front board's bottom edge
fb_top   = fb_bot + 54;

// board coordinates -> enclosure coordinates
function fbx(x) = x - 138;                    // front board: KiCad x
function fbz(y) = fb_top - (y - 100);         // front board: KiCad y
function mbx(x) = x - 132;                    // main board: KiCad x
function mby(y) = mb_front + (156 - y);       // main board: KiCad y

// ---------------------------------------------------------------- body
// top corners use R, bottom corners Rb; insetting both radii gives a uniform wall
module section(yt, yb, w, h, inset) for (sx = [-1, 1]) {
    translate([sx * (w / 2 - R),  yt, h - R]) sphere(r = max(R - inset, 0.01));
    translate([sx * (w / 2 - Rb), yb, Rb])    sphere(r = max(Rb - inset, 0.01));
}
// two hulls: a wide front that narrows quickly to Y_taper, then a straight rear section
module body(inset = 0) {
    hull() {
        section(R, Rb, W_front, H_front, inset);
        section(Y_taper, Y_taper, W_rear, top_z(Y_taper), inset);
        if (inset == 0)   // square off the front-bottom edge so the lip meets a flat face
            translate([-(W_front / 2 - Rb), 0, 0]) cube([W_front - 2 * Rb, lip_t, Rb]);
    }
    hull() {
        section(Y_taper, Y_taper, W_rear, top_z(Y_taper), inset);
        section(D - R, D - Rb, W_rear, H_rear, inset);
    }
}
module shell() difference() { body(0); body(wall); }

// half-spaces that define the split
module zone_A() {
    translate([-100, -50, -50]) cube([200, 50 + wall, 200]);           // front panel
    translate([-100, D - wall, -50]) cube([200, 50, 200]);             // rear wall
    translate([-100, -50, -50]) cube([200, 200, 50 + floor_t]);        // floor
}

// ---------------------------------------------------------------- feature positions
fb_holes   = [[103.5, 103.5], [172.5, 103.5], [103.5, 150.5], [172.5, 150.5]];
mb_holes   = [[103.5, 103.5], [160, 123.5], [117.5, 152.5], [159.5, 151.5]];
buttons    = [[115, 139], [138, 139], [161, 139]];                      // SW2..SW4 centres
encoder    = [153, 115];                                                // SW1 shaft
oled_mod   = [106, 133.3, 101];                                         // x1, x2, top y
join_screws= [[-35, 14], [35, 14], [-34.5, 60], [34.5, 60]];            // base -> cover
j_left     = [mby(133), mb_top + jack_z];      // J3 PHONES (Y, Z), left side
j_right    = [mby(140), mb_top + jack_z];      // J1 KEY, right side
j_rear     = [mbx(157), mb_top + jack_z];      // J2 RIG (X, Z), rear
usb        = [mbx(128), mb_top + usb_z];       // RP2040-Zero USB-C (X, Z), rear
wheel      = [mby(148), mb_top + wheel_z];     // RV1 (Y, Z), left side; edge at X = -34.5

// ---------------------------------------------------------------- helpers
module label_front(t, x, z, s = 5)
    translate([x, label_d, z]) rotate([90, 0, 0])
        linear_extrude(label_d + 1) text(t, size = s, font = font, halign = "center", valign = "center");
module arrow_front(x, z, dir) // dir = -1 left, +1 right
    translate([x, label_d, z]) rotate([90, 0, 0]) linear_extrude(label_d + 1)
        scale([dir, 1]) polygon([[4.5, 0], [0.5, 3], [0.5, 1.1], [-4.5, 1.1], [-4.5, -1.1], [0.5, -1.1], [0.5, -3]]);
module label_side(t, side, y, z, s = 4) {   // side -1 = left, +1 = right
    xo = side * W_rear / 2;
    translate([xo - side * label_d, y, z]) rotate([90, 0, side > 0 ? 90 : -90])
        linear_extrude(label_d + 1) text(t, size = s, font = font, halign = "center", valign = "center");
}
module label_rear(t, x, z, s = 4)
    translate([x, D - label_d, z]) rotate([90, 0, 180])
        linear_extrude(label_d + 1) text(t, size = s, font = font, halign = "center", valign = "center");
module rounded_slot(w, h, r, len)
    rotate([90, 0, 0]) linear_extrude(len, center = true)
        offset(r) square([w - 2 * r, h - 2 * r], center = true);
// the hull's top plane sits R*(1/cos(tilt)-1) above top_z() because it is tangent to the corner spheres
module top_frame() translate([0, spk_y, top_z(spk_y) + R * (1 / cos(tilt) - 1)]) rotate([-tilt, 0, 0]) children();

// ---------------------------------------------------------------- piece A: base
module base() {
    difference() {
        union() {
            intersection() { shell(); zone_A(); }
            intersection() { body(0); translate([-100, -50, -50]) cube([200, 200, 50 + floor_t]); }
            // radio lip: the front face continues 1/4" below the bottom
            hull() for (sx = [-1, 1]) {
                translate([sx * (W_front / 2 - Rb - lip_r), 0, -lip_drop + lip_r]) rotate([-90, 0, 0]) cylinder(r = lip_r, h = lip_t);
                translate([sx * (W_front / 2 - Rb - 0.01), 0, 0.5]) rotate([-90, 0, 0]) cylinder(r = 0.01, h = lip_t);
            }
            // locating rim on the floor, just inside the cover's walls
            difference() {
                intersection() {
                    difference() { body(wall + 0.2); body(wall + 1.4); }
                    translate([-100, -50, floor_t]) cube([200, 200, 2]);
                }
                for (p = join_screws) translate([p[0], p[1], 0]) cylinder(d = boss_d + 1, h = 20);
            }
            // main board standoffs
            for (h = mb_holes) translate([mbx(h[0]), mby(h[1]), floor_t - 0.01]) cylinder(d = 7, h = standoff);
            // front board bosses on the inside of the front panel
            for (h = fb_holes) translate([fbx(h[0]), wall - 0.01, fbz(h[1])])
                rotate([-90, 0, 0]) cylinder(d = 5.8, h = gap_front + 0.01);
        }
        // pilots
        for (h = mb_holes) translate([mbx(h[0]), mby(h[1]), floor_t + standoff - 7]) cylinder(d = pilot_d, h = 8);
        for (h = fb_holes) translate([fbx(h[0]), wall - 1.5, fbz(h[1])]) rotate([-90, 0, 0]) cylinder(d = pilot_d, h = gap_front + 2);
        // join screws: clearance + counterbore from below
        for (p = join_screws) translate([p[0], p[1], -1]) {
            cylinder(d = clear_d, h = floor_t + 2);
            cylinder(d = head_d, h = head_h + 1);
        }
        // magnet pockets (glue the magnets in)
        for (m = mag_pos) translate([m[0], m[1], -0.01]) cylinder(d = mag_d, h = mag_h);
        // front panel openings
        ox = fbx((oled_mod[0] + oled_mod[1]) / 2); oz = fbz(oled_mod[2] + oled_dz);
        translate([ox, wall / 2, oz]) rounded_slot(oled_win[0], oled_win[1], 1, wall + 2);
        translate([ox, 0, oz]) hull() {                 // chamfer on the outside
            translate([0, 0.01, 0]) rounded_slot(oled_win[0] + 2.4, oled_win[1] + 2.4, 1.5, 0.02);
            translate([0, 1.2, 0])  rounded_slot(oled_win[0], oled_win[1], 1, 0.02);
        }
        translate([fbx(encoder[0]), -1, fbz(encoder[1])]) rotate([-90, 0, 0]) cylinder(d = enc_hole, h = wall + 2);
        for (b = buttons) translate([fbx(b[0]), -1, fbz(b[1])]) rotate([-90, 0, 0]) cylinder(d = btn_hole, h = wall + 2);
        // front labels: numbers above the buttons, arrows below 1 and 3
        for (i = [0 : 2]) label_front(str(i + 1), fbx(buttons[i][0]), fbz(buttons[i][1]) + 10.5);
        arrow_front(fbx(buttons[0][0]), fbz(buttons[0][1]) - 10.5, -1);
        arrow_front(fbx(buttons[2][0]), fbz(buttons[2][1]) - 10.5, 1);
        // rear: rig jack and USB-C
        translate([j_rear[0], D - wall - 1, j_rear[1]]) rotate([-90, 0, 0]) cylinder(d = 11, h = wall + 2);
        translate([usb[0], D - wall / 2, usb[1]]) rounded_slot(13, 7.5, 2.5, wall + 2);
        label_rear("RIG", j_rear[0], j_rear[1] + 9);
        label_rear("USB", usb[0], usb[1] + 7.5);
    }
}

// ---------------------------------------------------------------- piece B: cover
module speaker_mount() top_frame() {
    ring_h = spk_h + 1.2;
    difference() {
        translate([0, 0, -wall - ring_h]) cylinder(d = spk_d + 4.4, h = ring_h + 0.5);
        translate([0, 0, -wall - ring_h - 1]) cylinder(d = spk_d + 0.6, h = ring_h + 2);
        // slots either side of each catch so the tongues can flex
        for (a = [0, 120, 240]) rotate([0, 0, a]) for (s = [-1, 1])
            translate([spk_d / 2 - 1, s * 4.5 - 0.5, -wall - ring_h - 1]) cube([5, 1, ring_h - 1 + 1]);
    }
    // catches that snap over the speaker rim
    for (a = [0, 120, 240]) rotate([0, 0, a])
        translate([spk_d / 2 + 0.3, 0, -wall - spk_h - 0.1]) hull() {
            translate([-0.01, -3.5, -1.0]) cube([0.01, 7, 1.0]);
            translate([-0.9, -3.5, -0.2]) cube([0.9, 7, 0.2]);
        }
}
module cover() {
    difference() {
        union() {
            difference() { shell(); zone_A(); }
            speaker_mount();
            for (p = join_screws) intersection() {
                body(0.3);
                translate([p[0], p[1], floor_t]) cylinder(d = boss_d, h = standoff);
            }
        }
        for (p = join_screws) translate([p[0], p[1], floor_t - 1]) cylinder(d = pilot_d, h = standoff + 2);
        // grille
        top_frame() for (i = [-6 : 6], j = [-6 : 6]) {
            x = i * 3.6 + (abs(j) % 2) * 1.8; y = j * 3.6 * sin(60);
            if (sqrt(x * x + y * y) <= grille_r)
                translate([x, y, -wall - 1]) cylinder(d = grille_hole, h = wall + 3, $fn = 16);
        }
        // side jacks (plug body passes into the wall so the plug seats fully)
        translate([-W_front / 2 - 1, j_left[0], j_left[1]])  rotate([0, 90, 0]) cylinder(d = 11, h = 10);
        translate([W_front / 2 - 9, j_right[0], j_right[1]]) rotate([0, 90, 0]) cylinder(d = 11, h = 10);
        // thumbwheel scallop on the left side
        translate([-34.6 - 10, wheel[0], wheel[1] - 4.5]) cylinder(r = 10, h = 9, $fn = 96);
        label_side("PHONES", -1, j_left[0], j_left[1] + 9);
        label_side("VOL",    -1, wheel[0], wheel[1] + 9);
        label_side("KEY",     1, j_right[0], j_right[1] + 9);
    }
}

// ---------------------------------------------------------------- board ghosts for checking fit
module boards() {
    color("green", 0.6) {
        translate([-38, fb_front, fb_bot]) cube([76, pcb_t, 54]);
        translate([-32, mb_front, mb_bot]) cube([64, 56, pcb_t]);
    }
    color("silver") translate([mbx(128) - 9, mby(111.75) - 11.75, mb_top + 11]) cube([18, 23.5, 1]);
}

if (part == "base") base();
else if (part == "cover") translate([0, 0, 0]) cover();
else if (part == "boards") boards();
else {
    color("white") base();
    color("deepskyblue", 0.55) cover();
    boards();
}
