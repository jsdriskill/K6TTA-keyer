#ifndef MESSAGES_H
#define MESSAGES_H

#include "config.h"

/* Three stored messages (up to MSG_MAX_LEN characters each) on buttons
 * PIN_MSG1..3 (active low).
 *
 *  - short press: send the message; if one is already sending, abort it.
 *    An empty slot goes to edit mode instead.
 *  - hold 3 s: edit that slot.
 *
 * Edit mode: the encoder picks the character at the cursor, the encoder
 * button stores it and advances; button 1 / button 2 move the cursor back /
 * forward without changing anything. Selecting "done" and pressing the
 * encoder button truncates the message at the cursor and saves it. Filling
 * all MSG_MAX_LEN positions saves and exits automatically. */

#define MSG_HOLD_MS      3000
#define MSG_DEBOUNCE_MS  20

/* Character choices, in encoder order. Choice 0 is "done". */
#define MSG_CHOICES      42
char msg_choice_char(int choice);       /* 0 for "done" */

typedef struct {
    uint8_t slot;                       /* 0..MSG_SLOTS-1 */
    uint8_t pos;                        /* cursor, 0..MSG_MAX_LEN-1 */
    uint8_t len;                        /* characters stored so far */
    uint8_t sel;                        /* choice shown at the cursor (0 = done) */
    char    text[MSG_MAX_LEN + 1];      /* committed text, NUL-terminated */
} MsgEditView;

void msg_init(void);

/* Call every main-loop pass. enabled = false while the setup menu is open
 * (button presses are then ignored). enc_delta / enc_click are only used
 * while editing; the caller must not act on them itself in that case. */
void msg_service(bool enabled, int8_t enc_delta, bool enc_click);

/* Same logic with the button levels passed in (true = pressed): used by msg_service and by tests. */
void msg_step(uint32_t now, const bool pressed[MSG_SLOTS], bool enabled, int8_t enc_delta, bool enc_click);

bool msg_edit_active(void);
void msg_edit_view(MsgEditView *v);

#endif
