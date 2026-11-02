#ifndef DISPLAY_H
#define DISPLAY_H

#include "config.h"

/* number of setup menu pages */
#define MENU_ITEM_COUNT 9

void display_init(void);
void display_update_ui(bool menu_active, uint8_t menu_item);   /* render + one flush step */
void display_render(bool menu_active, uint8_t menu_item);     /* build the frame (no I2C) */
void display_flush_step(void);                                /* send one changed chunk, if any */
void display_render_text(const char *str, uint8_t x, uint8_t y);

#endif
