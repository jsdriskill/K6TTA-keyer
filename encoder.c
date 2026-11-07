#include "encoder.h"
#include "config.h"
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/sync.h"

static volatile int8_t enc_delta = 0;

static uint8_t enc_last_state = 0;   /* previous (A<<1)|B */
static int8_t  enc_accum = 0;        /* transitions not yet turned into a detent step */
static int8_t  enc_last_dir = 0;     /* +1 / -1, used to resolve skipped states */

/*
 * Quadrature transition table, indexed by (previous_state << 2) | new_state.
 * +1 / -1 are the single-step transitions (same direction convention as the
 * original decoder); 0 means no change or an invalid two-bit jump.
 */
static const int8_t enc_table[16] = {
    /* 0000 */  0, /* 0001 */ -1, /* 0010 */ +1, /* 0011 */  0,
    /* 0100 */ +1, /* 0101 */  0, /* 0110 */  0, /* 0111 */ -1,
    /* 1000 */ -1, /* 1001 */  0, /* 1010 */  0, /* 1011 */ +1,
    /* 1100 */  0, /* 1101 */ +1, /* 1110 */ -1, /* 1111 */  0,
};

static void gpio_callback(uint gpio, uint32_t events) {
    (void)events;
    if (gpio != PIN_ENC_A && gpio != PIN_ENC_B) {
        return;
    }

    uint8_t state = (uint8_t)((gpio_get(PIN_ENC_A) << 1) | gpio_get(PIN_ENC_B));
    uint8_t idx = (uint8_t)((enc_last_state << 2) | state);
    enc_last_state = state;

    int8_t step = enc_table[idx];
    if (step == 0) {
        /* Both bits changed at once: a state was skipped (IRQ latency or a
         * fast spin). Direction is ambiguous, so assume it kept going the
         * same way and count the two missed transitions. Anything else
         * (no change, e.g. a glitch shorter than the IRQ latency) is ignored. */
        if (idx == 0b0011 || idx == 0b0110 || idx == 0b1001 || idx == 0b1100) {
            step = (int8_t)(enc_last_dir * 2);
        }
        if (step == 0) {
            return;
        }
    }
    enc_last_dir = (step > 0) ? 1 : -1;

    /* One reported step per detent, not one per quadrature transition. A
     * bounce that reverses direction subtracts what it added, so contact
     * bounce cancels out instead of being counted. */
    enc_accum += step;
    while (enc_accum >= ENC_STEPS_PER_DETENT) {
        enc_delta++;
        enc_accum -= ENC_STEPS_PER_DETENT;
    }
    while (enc_accum <= -ENC_STEPS_PER_DETENT) {
        enc_delta--;
        enc_accum += ENC_STEPS_PER_DETENT;
    }
}

void encoder_init(void) {
    gpio_init(PIN_ENC_A);
    gpio_set_dir(PIN_ENC_A, GPIO_IN);
    gpio_pull_up(PIN_ENC_A);

    gpio_init(PIN_ENC_B);
    gpio_set_dir(PIN_ENC_B, GPIO_IN);
    gpio_pull_up(PIN_ENC_B);

    gpio_init(PIN_ENC_SW);
    gpio_set_dir(PIN_ENC_SW, GPIO_IN);
    gpio_pull_up(PIN_ENC_SW);

    /* Start from the real pin state, not 0, so the first edge isn't misread. */
    enc_last_state = (uint8_t)((gpio_get(PIN_ENC_A) << 1) | gpio_get(PIN_ENC_B));
    enc_accum = 0;
    enc_last_dir = 0;

    gpio_set_irq_enabled_with_callback(PIN_ENC_A, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true, &gpio_callback);
    gpio_set_irq_enabled(PIN_ENC_B, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true);
}

int8_t encoder_get_delta(void) {
    uint32_t ints = save_and_disable_interrupts();
    int8_t d = enc_delta;
    enc_delta = 0;
    restore_interrupts(ints);
    return d;
}

/* Encoder push button: one click per press.
 *
 * The switch is debounced in both directions with a small state machine: a press
 * counts once the line has stayed low for ENC_SW_PRESS_MS, and the button is not
 * ready for another click until the line has stayed high for ENC_SW_RELEASE_MS.
 * Contact bounce on either edge (short pulses of the opposite level) is ignored,
 * and holding the button does not repeat. */
#define ENC_SW_PRESS_MS    20
#define ENC_SW_RELEASE_MS  50

static bool sw_pressed;         /* debounced state */
static bool sw_cand;            /* raw level being timed */
static uint32_t sw_since;       /* when sw_cand last changed */

bool encoder_button_pressed(void) {
    uint32_t now = to_ms_since_boot(get_absolute_time());
    bool raw = !gpio_get(PIN_ENC_SW);

    if (raw != sw_cand) {
        sw_cand = raw;
        sw_since = now;
    } else if (sw_cand != sw_pressed) {
        uint32_t need = sw_cand ? ENC_SW_PRESS_MS : ENC_SW_RELEASE_MS;
        if ((uint32_t)(now - sw_since) >= need) {
            sw_pressed = sw_cand;
            return sw_pressed;      /* true once, on the press */
        }
    }
    return false;
}
