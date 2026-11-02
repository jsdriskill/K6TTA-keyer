#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#include <stdbool.h>
#include "hardware/i2c.h"

#define PIN_PADDLE_DIT     2
#define PIN_PADDLE_DASH    3
#define PIN_TX_KEY         4
#define PIN_SIDETONE_PWM   5

/* Stored-message buttons: active low, internal pull-ups */
#define PIN_MSG1           9
#define PIN_MSG2           10
#define PIN_MSG3           11

#define PIN_ENC_A          6
#define PIN_ENC_B          7
#define PIN_ENC_SW         8

/* Quadrature transitions per physical detent (click). Most mechanical
 * encoders (e.g. EC11 with 20 detents) give 4; some give 2 (rests at both
 * 00 and 11) or 1. If one click moves the value by N, set this to N. */
#ifndef ENC_STEPS_PER_DETENT
#define ENC_STEPS_PER_DETENT 4
#endif

#define I2C_PORT           i2c0
#define PIN_I2C_SDA        12
#define PIN_I2C_SCL        13
#define SSD1306_ADDR       0x3C

#define MSG_SLOTS    3
#define MSG_MAX_LEN  32

typedef enum {
    KEYER_MODE_IAMBIC_B = 0,
    KEYER_MODE_IAMBIC_A,
    KEYER_MODE_ULTIMATE,
    KEYER_MODE_BUG,
    KEYER_MODE_STRAIGHT
} KeyerMode;

typedef struct __attribute__((packed)) {
    uint8_t  magic;
    uint8_t  wpm;
    uint8_t  sidetone_en;
    uint16_t sidetone_freq;
    uint8_t  weighting;
    uint8_t  dash_ratio;
    uint8_t  mode;
    uint8_t  paddle_swap;
    uint8_t  autospace;
    uint8_t  first_extension;
    uint8_t  show_text;         /* 1 = decoded text on the main screen, 0 = speed only. This byte held the
                                   sidetone volume (1..10) in older saves, so anything but 0 reads as on. */
    char     messages[MSG_SLOTS][MSG_MAX_LEN];   /* stored messages: NUL-terminated unless full; empty = first byte 0 */
} ConfigSettings;

extern ConfigSettings sys_config;

#endif
