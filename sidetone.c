#include "sidetone.h"

#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pwm.h"

#include "config.h"
#include "keyer.h"

/*
 * Sidetone square wave on GPIO5 (PIN_SIDETONE_PWM).
 *
 * The pin's PWM channel comes from the pin number (GPIO n -> slice n/2,
 * channel A for even n, B for odd n); GPIO5 is channel B. The slice is shared
 * with GPIO4 (PIN_TX_KEY) but that pin is plain SIO, so it is not affected.
 * The PWM runs at the sidetone frequency with a 50 % duty cycle. While the
 * sidetone is off the pin is parked low as a normal output: stopping the PWM
 * slice alone would freeze the pin at whatever level it had, leaving DC across
 * a buzzer.
 */
static uint slice;
static uint chan;
static bool sidetone_on;

static void sidetone_pin_low(void) {
    gpio_put(PIN_SIDETONE_PWM, 0);
    gpio_set_dir(PIN_SIDETONE_PWM, GPIO_OUT);
    gpio_set_function(PIN_SIDETONE_PWM, GPIO_FUNC_SIO);
}

void keyer_update_sidetone_freq(void) {
    uint32_t freq = sys_config.sidetone_freq;
    if (freq < 100) {
        return;
    }
    if (freq > 4000) {
        freq = 4000;
    }

    /* Smallest integer divider that keeps the 16 bit counter in range, which
     * gives the finest pitch resolution (about 0.002 %). */
    uint32_t clk = clock_get_hz(clk_sys);
    uint32_t divider = clk / (freq * 65536u) + 1;
    uint32_t wrap = clk / (freq * divider) - 1;

    pwm_set_clkdiv(slice, (float)divider);
    pwm_set_wrap(slice, (uint16_t)wrap);
    pwm_set_chan_level(slice, chan, (wrap + 1) / 2);
}

void keyer_set_sidetone(bool active) {
    bool want = sys_config.sidetone_en && active;
    if (want == sidetone_on) {
        return;                     /* called every tick in some modes: do nothing if unchanged */
    }
    sidetone_on = want;
    if (want) {
        pwm_set_counter(slice, 0);
        pwm_set_enabled(slice, true);
        gpio_set_function(PIN_SIDETONE_PWM, GPIO_FUNC_PWM);
    } else {
        pwm_set_enabled(slice, false);
        sidetone_pin_low();
    }
}

void sidetone_init(void) {
    slice = pwm_gpio_to_slice_num(PIN_SIDETONE_PWM);
    chan = pwm_gpio_to_channel(PIN_SIDETONE_PWM);
    gpio_init(PIN_SIDETONE_PWM);
    sidetone_pin_low();
    pwm_set_enabled(slice, false);
    keyer_update_sidetone_freq();
    sidetone_on = false;
}
