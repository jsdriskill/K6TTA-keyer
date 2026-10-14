#ifndef SIDETONE_H
#define SIDETONE_H

#include <stdbool.h>

/* Local sidetone: a sine wave on PIN_SIDETONE_PWM, made by PWM used as a
 * one-pin DAC. keyer_set_sidetone() / keyer_update_sidetone_freq() /
 * keyer_update_sidetone_volume() (keyer.h) are implemented in sidetone.c. */
void sidetone_init(void);
void sidetone_service(void);        /* call often from the main loop (core 0) */

/* The PWM wrap interrupt handler: one call = one output sample. Public only so
 * the host-side tests can drive it. */
void sidetone_sample_isr(void);

#define SIDETONE_PWM_WRAP   2047u   /* 11 bit steps, about 61 kHz carrier and sample rate */

#endif
