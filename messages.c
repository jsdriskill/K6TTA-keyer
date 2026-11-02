#include "messages.h"

#include <string.h>
#include "pico/stdlib.h"
#include "flash_settings.h"
#include "keyer.h"

static const char choices[MSG_CHOICES + 1] = "\0 ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?/";

char msg_choice_char(int choice) {
    if (choice < 0 || choice >= MSG_CHOICES) {
        return 0;
    }
    return choices[choice];
}

static int choice_of(char c) {
    for (int i = 1; i < MSG_CHOICES; i++) {
        if (choices[i] == c) {
            return i;
        }
    }
    return 1;               /* not a known character: start on space */
}

typedef struct {
    bool     cand, stable;
    uint32_t since;         /* when cand last changed */
    uint32_t press_t;       /* when the press was accepted */
    bool     hold_done;     /* hold handled (or press ignored): the release does nothing */
    bool     aborted;       /* this press already aborted a send */
} Button;

static Button btn[MSG_SLOTS];

/* ---- edit state ---- */
static bool    editing;
static uint8_t e_slot, e_pos, e_len, e_sel;
static char    e_text[MSG_MAX_LEN + 1];

static int sel_at(int pos) {
    return pos < e_len ? choice_of(e_text[pos]) : 0;
}

static void edit_begin(int slot) {
    e_slot = (uint8_t)slot;
    memcpy(e_text, sys_config.messages[slot], MSG_MAX_LEN);
    e_text[MSG_MAX_LEN] = 0;
    e_len = (uint8_t)strlen(e_text);
    e_pos = 0;
    e_sel = (uint8_t)sel_at(0);
    editing = true;
}

static void edit_finish(void) {
    memset(sys_config.messages[e_slot], 0, MSG_MAX_LEN);
    memcpy(sys_config.messages[e_slot], e_text, e_len);
    settings_save();
    editing = false;
}

static void edit_click(void) {
    if (e_sel == 0) {                       /* done: keep what is before the cursor */
        e_len = e_pos;
        e_text[e_len] = 0;
        edit_finish();
        return;
    }
    e_text[e_pos] = choices[e_sel];
    if (e_pos == e_len) {
        e_len++;
        e_text[e_len] = 0;
    }
    e_pos++;
    if (e_pos >= MSG_MAX_LEN) {
        edit_finish();
        return;
    }
    e_sel = (uint8_t)sel_at(e_pos);
}

static void edit_move(int dir) {
    int p = (int)e_pos + dir;
    int max = e_len < MSG_MAX_LEN - 1 ? e_len : MSG_MAX_LEN - 1;
    if (p < 0 || p > max) {
        return;
    }
    e_pos = (uint8_t)p;
    e_sel = (uint8_t)sel_at(p);             /* an unstored change is dropped */
}

static void edit_turn(int delta) {
    int s = ((int)e_sel + delta) % MSG_CHOICES;
    if (s < 0) {
        s += MSG_CHOICES;
    }
    e_sel = (uint8_t)s;
}

/* ---- buttons ---- */
static void on_press(int i, bool enabled) {
    Button *b = &btn[i];
    b->hold_done = false;
    b->aborted = false;
    if (!enabled) {
        b->hold_done = true;                /* ignored, including its release */
    } else if (editing) {
        if (i == 0) {
            edit_move(-1);
        } else if (i == 1) {
            edit_move(+1);
        }
        b->hold_done = true;
    } else if (keyer_tx_busy()) {
        keyer_msg_abort();
        b->aborted = true;
    }
}

static void on_release(int i) {
    Button *b = &btn[i];
    if (b->hold_done || b->aborted || editing) {
        return;
    }
    if (sys_config.messages[i][0] == 0) {
        edit_begin(i);
    } else {
        char text[MSG_MAX_LEN + 1];
        memcpy(text, sys_config.messages[i], MSG_MAX_LEN);
        text[MSG_MAX_LEN] = 0;
        keyer_msg_send(text);
    }
}

void msg_step(uint32_t now, const bool pressed[MSG_SLOTS], bool enabled, int8_t enc_delta, bool enc_click) {
    if (editing) {
        if (enc_delta != 0) {
            edit_turn(enc_delta);
        }
        if (enc_click) {
            edit_click();
        }
    }

    for (int i = 0; i < MSG_SLOTS; i++) {
        Button *b = &btn[i];
        if (pressed[i] != b->cand) {
            b->cand = pressed[i];
            b->since = now;
        } else if (b->cand != b->stable && (uint32_t)(now - b->since) >= MSG_DEBOUNCE_MS) {
            b->stable = b->cand;
            if (b->stable) {
                b->press_t = now;
                on_press(i, enabled);
            } else {
                on_release(i);
            }
        }
        if (b->stable && !b->hold_done && (uint32_t)(now - b->press_t) >= MSG_HOLD_MS) {
            b->hold_done = true;
            if (enabled && !editing) {
                edit_begin(i);
            }
        }
    }
}

void msg_init(void) {
    static const uint pins[MSG_SLOTS] = { PIN_MSG1, PIN_MSG2, PIN_MSG3 };
    for (int i = 0; i < MSG_SLOTS; i++) {
        gpio_init(pins[i]);
        gpio_set_dir(pins[i], GPIO_IN);
        gpio_pull_up(pins[i]);
    }
}

void msg_service(bool enabled, int8_t enc_delta, bool enc_click) {
    static const uint pins[MSG_SLOTS] = { PIN_MSG1, PIN_MSG2, PIN_MSG3 };
    bool pressed[MSG_SLOTS];
    for (int i = 0; i < MSG_SLOTS; i++) {
        pressed[i] = !gpio_get(pins[i]);
    }
    msg_step(to_ms_since_boot(get_absolute_time()), pressed, enabled, enc_delta, enc_click);
}

bool msg_edit_active(void) {
    return editing;
}

void msg_edit_view(MsgEditView *v) {
    v->slot = e_slot;
    v->pos = e_pos;
    v->len = e_len;
    v->sel = e_sel;
    memcpy(v->text, e_text, sizeof(v->text));
}
