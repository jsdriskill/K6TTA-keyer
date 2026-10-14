#include "sidetone.h"

#include <math.h>

#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/pwm.h"
#include "hardware/sync.h"

#include "config.h"
#include "keyer.h"

/*
 * Sidetone sine wave on GPIO5.
 *
 * The RP2040 has no DAC, so the pin's PWM slice is run as one: the counter
 * wraps every 2048 system clocks (about 61 kHz, far above hearing and above
 * what a small speaker or piezo reproduces) and the wrap interrupt writes the
 * next sample into the compare register, so one interrupt is one sample and
 * nothing needs a separate timer. The speaker's own low-pass action turns the
 * duty cycle back into the sine. The wave is unipolar, duty = gain * (1 + sin) / 2,
 * so at rest the pin is low and the attack/release envelope also ramps the DC
 * part: no step, no click.
 *
 * GPIO n is PWM slice n/2, channel A for even n and B for odd n; GPIO5 is
 * channel B of the slice it shares with GPIO4 (PIN_TX_KEY), which is plain SIO
 * and unaffected. While silent the pin is parked low as a normal output:
 * a stopped PWM slice would freeze the pin at its last level.
 */
#define ENV_RAMP_MS    4              /* attack / release, as the USB audio sidetone */
#define START_PHASE    0xC0000000u    /* sin = -1: the wave starts at duty 0 */

static uint slice;
static uint chan;
static uint16_t sine_tab[257];        /* 0..65535 = (1 + sin) / 2; [256] repeats [0] for interpolation */

static volatile uint32_t phase;       /* 32 bit phase accumulator */
static volatile uint32_t phase_inc;
static volatile uint32_t env;         /* 0..65535 */
static volatile uint32_t env_step;
static volatile uint32_t gain;        /* 0..65535, from the volume setting */
static volatile bool want;            /* key down and sidetone enabled */
static volatile bool running;         /* PWM slice running (tone sounding or fading) */
static volatile bool park_pending;    /* slice stopped, pin still to be parked low */

static void pin_low(void) {
    gpio_put(PIN_SIDETONE_PWM, 0);
    gpio_set_dir(PIN_SIDETONE_PWM, GPIO_OUT);
    gpio_set_function(PIN_SIDETONE_PWM, GPIO_FUNC_SIO);
}

/* One output sample. Runs from RAM, once per PWM period. */
void __not_in_flash_func(sidetone_sample_isr)(void) {
    pwm_clear_irq(slice);

    uint32_t e = env;
    if (want) {
        e += env_step;
        if (e > 65535u) {
            e = 65535u;
        }
    } else if (e > env_step) {
        e -= env_step;
    } else {
        e = 0;
    }
    env = e;

    uint32_t p = phase + phase_inc;
    phase = p;
    uint32_t idx = p >> 24;
    uint32_t frac = (p >> 16) & 0xFFu;
    int32_t a = sine_tab[idx];
    int32_t b = sine_tab[idx + 1];
    uint32_t s = (uint32_t)(a + (((b - a) * (int32_t)frac) >> 8));      /* linear interpolation */

    uint32_t g = (e * gain) >> 16;
    uint32_t level = (((s * g) >> 16) * SIDETONE_PWM_WRAP) >> 16;
    pwm_set_chan_level(slice, chan, level);

    if (e == 0 && !want) {
        pwm_set_enabled(slice, false);        /* faded out: stop; the main loop parks the pin */
        running = false;
        park_pending = true;
    }
}

void keyer_update_sidetone_freq(void) {
    uint32_t freq = sys_config.sidetone_freq;
    if (freq < 100) {
        return;
    }
    if (freq > 4000) {
        freq = 4000;
    }
    /* sample rate = system clock / (wrap + 1) */
    uint32_t clk = clock_get_hz(clk_sys);
    phase_inc = (uint32_t)(((uint64_t)freq << 32) * (SIDETONE_PWM_WRAP + 1u) / clk);
}

void keyer_update_sidetone_volume(void) {
    uint32_t vol = sys_config.sidetone_vol;
    if (vol < SIDETONE_VOL_MIN || vol > SIDETONE_VOL_MAX) {
        vol = SIDETONE_VOL_MAX;
    }
    /* amplitude: 1 = 10 % of the maximum swing, 10 = the full 0..Vdd swing */
    gain = 65535u * vol / SIDETONE_VOL_MAX;
}

void keyer_set_sidetone(bool active) {
    bool w = sys_config.sidetone_en && active;
    if (w == want) {
        return;                     /* called every tick in some modes: nothing to do if unchanged */
    }
    uint32_t irq_state = save_and_disable_interrupts();
    want = w;
    if (w && !running) {
        phase = START_PHASE;
        env = 0;
        pwm_set_chan_level(slice, chan, 0);
        pwm_set_counter(slice, 0);
        gpio_set_function(PIN_SIDETONE_PWM, GPIO_FUNC_PWM);
        park_pending = false;
        running = true;
        pwm_set_enabled(slice, true);
    }
    restore_interrupts(irq_state);
}

void sidetone_service(void) {
    if (!park_pending) {
        return;
    }
    uint32_t irq_state = save_and_disable_interrupts();
    if (park_pending && !running) {
        pin_low();
        park_pending = false;
    }
    restore_interrupts(irq_state);
}

void sidetone_init(void) {
    for (int i = 0; i < 256; i++) {
        sine_tab[i] = (uint16_t)(32767.5f + 32767.0f * sinf(6.2831853f * (float)i / 256.0f));
    }
    sine_tab[256] = sine_tab[0];

    slice = pwm_gpio_to_slice_num(PIN_SIDETONE_PWM);
    chan = pwm_gpio_to_channel(PIN_SIDETONE_PWM);

    want = false;
    running = false;
    park_pending = false;
    env = 0;

    uint32_t clk = clock_get_hz(clk_sys);
    uint32_t sample_rate = clk / (SIDETONE_PWM_WRAP + 1u);
    env_step = 65536u * 1000u / (sample_rate * ENV_RAMP_MS);

    gpio_init(PIN_SIDETONE_PWM);
    pin_low();
    pwm_set_enabled(slice, false);
    pwm_set_clkdiv(slice, 1.0f);
    pwm_set_wrap(slice, SIDETONE_PWM_WRAP);
    pwm_set_chan_level(slice, chan, 0);

    keyer_update_sidetone_freq();
    keyer_update_sidetone_volume();

    pwm_clear_irq(slice);
    pwm_set_irq_enabled(slice, true);
    irq_set_exclusive_handler(PWM_IRQ_WRAP, sidetone_sample_isr);
    irq_set_enabled(PWM_IRQ_WRAP, true);
}
