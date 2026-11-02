#include "display.h"
#include "font5x8.h"
#include "font_large.h"
#include "messages.h"
#include "textview.h"

#include <stdio.h>
#include <string.h>
#include "hardware/i2c.h"
#include "pico/stdlib.h"

static uint8_t frame_buffer[1024];

static const char *mode_name(uint8_t mode) {
    switch (mode) {
        case KEYER_MODE_IAMBIC_B: return "IAMBIC-B";
        case KEYER_MODE_IAMBIC_A: return "IAMBIC-A";
        case KEYER_MODE_ULTIMATE: return "ULTIMATIC";
        case KEYER_MODE_BUG:      return "BUG";
        case KEYER_MODE_STRAIGHT: return "STRAIGHT";
        default:                  return "UNKNOWN";
    }
}

static void send_cmd(uint8_t cmd) {
    uint8_t buf[2] = {0x00, cmd};
    i2c_write_blocking(I2C_PORT, SSD1306_ADDR, buf, 2, false);
}

void display_init(void) {
    i2c_init(I2C_PORT, 400 * 1000);
    gpio_set_function(PIN_I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C_SDA);
    gpio_pull_up(PIN_I2C_SCL);

    uint8_t init_cmds[] = {
        0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40,
        0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x12,
        0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
    };
    for (size_t i = 0; i < sizeof(init_cmds); i++) {
        send_cmd(init_cmds[i]);
    }
    memset(frame_buffer, 0, sizeof(frame_buffer));
}

/* The frame is sent in 32 byte chunks, at most one per call, and only when it
 * differs from what the panel already shows. A blocking I2C transfer stalls
 * keyer_tick() (same loop), so a whole-frame refresh (~25 ms at 400 kHz) used
 * to stretch or delay keyed elements; one chunk takes about 1 ms. */
#define CHUNK_BYTES   32
#define CHUNKS_TOTAL  (sizeof(frame_buffer) / CHUNK_BYTES)
static uint8_t sent_buffer[1024];
static bool panel_valid;            /* false until the first full send */
static unsigned next_chunk;

static void flush_next_chunk(void) {
    for (unsigned n = 0; n < CHUNKS_TOTAL; n++) {
        unsigned c = (next_chunk + n) % CHUNKS_TOTAL;
        const uint8_t *src = &frame_buffer[c * CHUNK_BYTES];
        if (panel_valid && memcmp(src, &sent_buffer[c * CHUNK_BYTES], CHUNK_BYTES) == 0) {
            continue;
        }
        unsigned page = (c * CHUNK_BYTES) / 128;
        unsigned col = (c * CHUNK_BYTES) % 128;
        send_cmd(0xB0 + page);
        send_cmd(0x00 + (col & 0x0F));
        send_cmd(0x10 + (col >> 4));
        uint8_t buf[CHUNK_BYTES + 1];
        buf[0] = 0x40;
        memcpy(&buf[1], src, CHUNK_BYTES);
        i2c_write_blocking(I2C_PORT, SSD1306_ADDR, buf, sizeof(buf), false);
        memcpy(&sent_buffer[c * CHUNK_BYTES], src, CHUNK_BYTES);
        next_chunk = (c + 1) % CHUNKS_TOTAL;
        if (next_chunk == 0) {
            panel_valid = true;         /* a full pass has gone out */
        }
        return;
    }
    panel_valid = true;
}

void display_render_text(const char *str, uint8_t x, uint8_t y) {
    uint8_t page = y / 8;
    if (page > 7) {
        return;
    }
    while (*str && x < 128) {
        unsigned char c = (unsigned char)*str++;
        if (c < 32 || c > 126) {
            c = '?';
        }
        const uint8_t *glyph = font5x8[c - 32];
        for (int col = 0; col < 5 && x < 128; col++, x++) {
            frame_buffer[page * 128 + x] = glyph[col];
        }
        if (x < 128) {
            frame_buffer[page * 128 + x] = 0x00;
            x++;
        }
    }
}

#define SCREEN_W        128
#define SCREEN_H        64
#define MODE_LINE_Y      56   /* bottom text line (one 8-px page) */
#define NUMBER_GAP       4    /* pixels between large digits */
#define NUMBER_MAX_DIGITS 3   /* wpm is uint8_t: at most 255 */

static void set_pixel(int x, int y) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) {
        return;
    }
    frame_buffer[(y / 8) * SCREEN_W + x] |= (uint8_t)(1u << (y % 8));
}

static void clear_pixel(int x, int y) {
    if (x < 0 || x >= SCREEN_W || y < 0 || y >= SCREEN_H) {
        return;
    }
    frame_buffer[(y / 8) * SCREEN_W + x] &= (uint8_t)~(1u << (y % 8));
}

/* Message editor characters: the 5x8 font at 2x, in a cell 11 px wide (10 px
 * glyph + 1 px gap) and 16 px tall. The glyph sits one pixel down so that
 * rows 0 and 15 stay blank. Only the comma uses the font's bottom row, and
 * that row is clipped to its first pixel row. The cursor is a white box one
 * pixel larger than the glyph on every side (12 x 16 px, overlapping only the
 * blank gap columns of its neighbours) with the glyph cut out of it. */
#define BIG_PITCH_X       11
#define BIG_PITCH_Y       16
#define EDIT_CELLS_PER_LINE  11     /* 11 * 11 = 121 pixels */
#define EDIT_LINES        4         /* 4 * 16 = the whole screen */
#define EDIT_X0           3

static void render_big_cell(char c, int x, int y, bool inverted) {
    if (c < 32 || c > 126) {
        c = '?';
    }
    if (inverted) {
        for (int yy = y; yy < y + BIG_PITCH_Y; yy++) {
            for (int xx = x - 1; xx <= x + 10; xx++) {
                set_pixel(xx, yy);
            }
        }
    }
    const uint8_t *glyph = font5x8[c - 32];
    for (int col = 0; col < 5; col++) {
        for (int row = 0; row < 8; row++) {
            if (!((glyph[col] >> row) & 1)) {
                continue;
            }
            for (int dy = 0; dy < 2; dy++) {
                int py = y + 1 + 2 * row + dy;
                if (py >= y + BIG_PITCH_Y) {
                    continue;
                }
                for (int dx = 0; dx < 2; dx++) {
                    if (inverted) {
                        clear_pixel(x + 2 * col + dx, py);
                    } else {
                        set_pixel(x + 2 * col + dx, py);
                    }
                }
            }
        }
    }
}

static void render_edit_cell(char c, int cell, bool inverted) {
    if (cell >= EDIT_CELLS_PER_LINE * EDIT_LINES) {
        return;
    }
    render_big_cell(c, EDIT_X0 + (cell % EDIT_CELLS_PER_LINE) * BIG_PITCH_X,
                    (cell / EDIT_CELLS_PER_LINE) * BIG_PITCH_Y, inverted);
}

/* After the encoder is turned the speed is shown for this long, then the text again. */
#define SPEED_VIEW_MS 3000
static uint32_t speed_view_until;
static bool speed_view_on;

void display_speed_view(void) {
    speed_view_until = to_ms_since_boot(get_absolute_time()) + SPEED_VIEW_MS;
    speed_view_on = true;
}

static bool show_text_view(void) {
    if (!textview_started()) {
        return false;                       /* speed at boot, until the first character */
    }
    if (sys_config.mode == KEYER_MODE_STRAIGHT || sys_config.mode == KEYER_MODE_BUG) {
        return false;                       /* nothing is decoded in these modes */
    }
    if (speed_view_on) {
        if ((int32_t)(to_ms_since_boot(get_absolute_time()) - speed_view_until) < 0) {
            return false;
        }
        speed_view_on = false;
    }
    return true;
}

static void render_text_view(void) {
    for (int r = 0; r < TEXT_ROWS; r++) {
        const char *line = textview_line(r);
        for (int c = 0; c < TEXT_COLS; c++) {
            if (line[c] != ' ') {
                render_edit_cell(line[c], r * EDIT_CELLS_PER_LINE + c, false);
            }
        }
    }
}

/* Message editor: the whole message wrapped over up to four lines, the cursor
 * cell inverted. "done" shows as an inverted END, drawn inline so the
 * characters after it move right rather than being hidden. A full message
 * with END in it needs 34 cells; 4 lines hold 44. The four lines use the whole
 * display, so there is no room for a title or key hints. */
static void render_message_editor(void) {
    MsgEditView v;
    msg_edit_view(&v);

    int cell = 0;
    for (int i = 0; i <= v.len && i < MSG_MAX_LEN; i++) {
        bool cursor = (i == v.pos);
        if (cursor && v.sel == 0) {
            const char *end = "END";
            for (int k = 0; k < 3; k++, cell++) {
                render_edit_cell(end[k], cell, true);
            }
            continue;
        }
        char c = cursor ? msg_choice_char(v.sel) : (i < v.len ? v.text[i] : 0);
        if (c == 0) {
            break;
        }
        render_edit_cell(c, cell, cursor);
        cell++;
    }
}

/* Draw one large digit with its top-left corner at (x, y). */
static void draw_large_digit(int digit, int x, int y) {
    const uint8_t *bits = font_large_digits[digit];
    for (int col = 0; col < LARGE_FONT_W; col++) {
        for (int row = 0; row < LARGE_FONT_H; row++) {
            if ((bits[col * LARGE_FONT_BYTES_PER_COL + row / 8] >> (row % 8)) & 1) {
                set_pixel(x + col, y + row);
            }
        }
    }
}

/* Draw a string of digits in the large font, centered horizontally and
 * vertically in the area above the mode line. Digits sit in fixed-width
 * cells, so the number does not shift as the speed changes. */
static void render_number_centered(const char *str, int area_h) {
    int n = (int)strlen(str);
    if (n > NUMBER_MAX_DIGITS) {
        n = NUMBER_MAX_DIGITS;
    }
    if (n == 0) {
        return;
    }
    int gap = NUMBER_GAP;
    if (n > 1 && n * LARGE_FONT_W + (n - 1) * gap > SCREEN_W) {
        gap = (SCREEN_W - n * LARGE_FONT_W) / (n - 1);   /* 3 digits: no gap */
    }
    int total_w = n * LARGE_FONT_W + (n - 1) * gap;
    int x0 = (SCREEN_W - total_w) / 2;
    int y0 = (area_h - LARGE_FONT_H) / 2;

    for (int i = 0; i < n; i++) {
        if (str[i] >= '0' && str[i] <= '9') {
            draw_large_digit(str[i] - '0', x0 + i * (LARGE_FONT_W + gap), y0);
        }
    }
}

void display_render(bool menu_active, uint8_t menu_item) {
    memset(frame_buffer, 0x00, sizeof(frame_buffer));
    char line[32];

    if (msg_edit_active()) {
        render_message_editor();
        return;
    }

    if (!menu_active && show_text_view()) {
        render_text_view();
        return;
    }

    if (!menu_active) {
        snprintf(line, sizeof(line), "%d", sys_config.wpm);
        render_number_centered(line, MODE_LINE_Y);
        display_render_text(mode_name(sys_config.mode), 0, MODE_LINE_Y);
    } else {
        display_render_text("SETUP MENU", 0, 0);
        switch (menu_item) {
            case 0:
                snprintf(line, sizeof(line), "MODE: %s", mode_name(sys_config.mode));
                break;
            case 1:
                snprintf(line, sizeof(line), "SIDE FREQ: %dHz", sys_config.sidetone_freq);
                break;
            case 2:
                snprintf(line, sizeof(line), "SIDE EN: %s", sys_config.sidetone_en ? "ON" : "OFF");
                break;
            case 3:
                snprintf(line, sizeof(line), "WEIGHT: %d%%", sys_config.weighting);
                break;
            case 4:
                snprintf(line, sizeof(line), "DASH RATIO: %d", sys_config.dash_ratio);
                break;
            case 5:
                snprintf(line, sizeof(line), "PADDLE SWAP: %s", sys_config.paddle_swap ? "YES" : "NO");
                break;
            case 6:
                snprintf(line, sizeof(line), "AUTOSPACE: %s", sys_config.autospace ? "ON" : "OFF");
                break;
            case 7:
                snprintf(line, sizeof(line), "1ST EXT: %dms", sys_config.first_extension);
                break;
            default:
                snprintf(line, sizeof(line), "SIDE VOL: %d/10", sys_config.sidetone_vol);
                break;
        }
        display_render_text(line, 0, 24);
        snprintf(line, sizeof(line), "ITEM %d/%d  CLICK=NEXT", menu_item + 1, MENU_ITEM_COUNT);
        display_render_text(line, 0, 48);
    }
}

/* Send at most one changed 32-byte chunk (about 0.7 ms of blocking I2C). The
 * main loop calls this on every pass while the picture differs from the panel,
 * so a changed picture reaches the panel within a few milliseconds instead of
 * showing half old, half new for a long time, and keyer_tick() still runs
 * between chunks. */
void display_flush_step(void) {
    flush_next_chunk();
}

void display_update_ui(bool menu_active, uint8_t menu_item) {
    display_render(menu_active, menu_item);
    display_flush_step();
}

