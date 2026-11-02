#include "flash_settings.h"

#include <string.h>
#include "hardware/flash.h"
#include "pico/flash.h"

#define FLASH_TARGET_OFFSET (1024 * 1024)
#define CONFIG_MAGIC 0x4B

ConfigSettings sys_config;

void settings_init(void) {
    const uint8_t *flash_target_contents = (const uint8_t *)(XIP_BASE + FLASH_TARGET_OFFSET);
    memcpy(&sys_config, flash_target_contents, sizeof(ConfigSettings));

    if (sys_config.magic != CONFIG_MAGIC) {
        sys_config.magic = CONFIG_MAGIC;
        sys_config.wpm = 20;
        sys_config.sidetone_en = 1;
        sys_config.sidetone_freq = 700;
        sys_config.weighting = 50;
        sys_config.dash_ratio = 30;
        sys_config.mode = KEYER_MODE_IAMBIC_B;
        sys_config.paddle_swap = 0;
        sys_config.autospace = 0;
        sys_config.first_extension = 0;
        sys_config.sidetone_vol = SIDETONE_VOL_DEFAULT;
        memset(sys_config.messages, 0, sizeof(sys_config.messages));
        settings_save();
    }

    /* Settings saved by older firmware have no volume byte (erased flash reads
     * 0xFF): keep the previous loudness, which was the maximum. */
    if (sys_config.sidetone_vol < SIDETONE_VOL_MIN || sys_config.sidetone_vol > SIDETONE_VOL_MAX) {
        sys_config.sidetone_vol = SIDETONE_VOL_DEFAULT;
    }

    /* Older saves have erased flash (0xFF) where the messages now live; any
     * slot holding a character that cannot be sent is cleared. */
    for (int s = 0; s < MSG_SLOTS; s++) {
        char *m = sys_config.messages[s];
        for (int i = 0; i < MSG_MAX_LEN && m[i] != 0; i++) {
            char c = m[i];
            bool ok = c == ' ' || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                      c == '.' || c == ',' || c == '?' || c == '/';
            if (!ok) {
                memset(m, 0, MSG_MAX_LEN);
                break;
            }
        }
    }
}

static void do_flash_write(void *param) {
    flash_range_erase(FLASH_TARGET_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(FLASH_TARGET_OFFSET, (const uint8_t *)param, FLASH_PAGE_SIZE);
}

void settings_save(void) {
    uint8_t buffer[FLASH_PAGE_SIZE];
    memset(buffer, 0xFF, FLASH_PAGE_SIZE);
    memcpy(buffer, &sys_config, sizeof(ConfigSettings));

    /* Core 1 runs the USB stack from flash, which is unreadable while flash
     * is erased or programmed, so it has to be paused first. flash_safe_execute()
     * does that (core 1 registers itself in usb_device.c) and also disables
     * interrupts on this core. USB audio drops out for the ~50 ms this takes. */
    flash_safe_execute(do_flash_write, buffer, 500);
}
