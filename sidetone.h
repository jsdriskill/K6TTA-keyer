#ifndef SIDETONE_H
#define SIDETONE_H

#include <stdbool.h>

/* Local sidetone: a 50 % duty square wave on PIN_SIDETONE_PWM from the PWM
 * hardware. keyer_set_sidetone() / keyer_update_sidetone_freq() (keyer.h) are
 * implemented in sidetone.c. */
void sidetone_init(void);

#endif
