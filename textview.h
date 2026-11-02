#ifndef TEXTVIEW_H
#define TEXTVIEW_H

#include <stdbool.h>

/* Scrolling text shown on the main screen: what the paddles sent (decoded)
 * and what the text sender / stored messages sent. A small screen model:
 * TEXT_ROWS lines of TEXT_COLS characters, word wrapped, scrolling up one
 * line at a time when the bottom line is full. Core 0 only. */

#define TEXT_ROWS 4
#define TEXT_COLS 11

void textview_put(char c);                  /* ' ' = word space; others are shown as given */
void textview_reset(void);                  /* blank the screen model (tests; the firmware never clears it) */
bool textview_started(void);                /* any character since boot */
const char *textview_line(int row);         /* TEXT_COLS characters, padded with spaces, NUL-terminated */

#endif
