#include "textview.h"

#include <string.h>

static char lines[TEXT_ROWS][TEXT_COLS + 1];
static int row, col;
static bool started;
static bool inited;

static void ensure(void) {
    if (inited) {
        return;
    }
    for (int r = 0; r < TEXT_ROWS; r++) {
        memset(lines[r], ' ', TEXT_COLS);
        lines[r][TEXT_COLS] = 0;
    }
    row = col = 0;
    inited = true;
}

static void newline(void) {
    if (row < TEXT_ROWS - 1) {
        row++;
    } else {
        memmove(lines[0], lines[1], (TEXT_ROWS - 1) * (TEXT_COLS + 1));
        memset(lines[TEXT_ROWS - 1], ' ', TEXT_COLS);
        lines[TEXT_ROWS - 1][TEXT_COLS] = 0;
    }
    col = 0;
}

void textview_put(char c) {
    ensure();
    if (c < ' ' || c > '~') {
        return;
    }
    started = true;

    if (c == ' ') {
        if (col == 0) {
            return;                         /* no spaces at the start of a line */
        }
        if (col >= TEXT_COLS) {
            newline();                      /* the space falls at the wrap */
            return;
        }
        lines[row][col++] = ' ';
        return;
    }

    if (col >= TEXT_COLS) {
        /* The line is full. Move the word being typed down to the next line,
         * unless it is the whole line, in which case it is split. */
        int ws = TEXT_COLS;
        while (ws > 0 && lines[row][ws - 1] != ' ') {
            ws--;
        }
        if (ws == 0) {
            newline();
        } else {
            char word[TEXT_COLS + 1];
            int n = TEXT_COLS - ws;
            memcpy(word, &lines[row][ws], (size_t)n);
            memset(&lines[row][ws], ' ', (size_t)n);
            newline();
            memcpy(lines[row], word, (size_t)n);
            col = n;
        }
    }
    lines[row][col++] = c;
}

void textview_reset(void) {
    inited = false;
    started = false;
    ensure();
}

bool textview_started(void) {
    return started;
}

const char *textview_line(int r) {
    ensure();
    if (r < 0 || r >= TEXT_ROWS) {
        r = 0;
    }
    return lines[r];
}
