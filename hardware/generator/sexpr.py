"""Minimal S-expression reader/writer for KiCad files."""
import re


class Str(str):
    """A quoted string token."""


_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("parse error at %d: %r" % (pos, text[pos:pos + 40]))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(Str(m.group(3).replace('\\"', '"').replace('\\\\', '\\')))
        elif m.group(4):
            stack[-1].append(m.group(4))
    assert len(stack) == 1, "unbalanced"
    return stack[0][0]


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def dump(e, indent=0):
    if isinstance(e, list):
        simple = all(not isinstance(x, list) for x in e)
        if simple or len(e) <= 1:
            return "(" + " ".join(dump(x) for x in e) + ")"
        out = "(" + " ".join(dump(x) for x in e if not isinstance(x, list))
        for x in e:
            if isinstance(x, list):
                out += "\n" + "  " * (indent + 1) + dump(x, indent + 1)
        return out + "\n" + "  " * indent + ")"
    if isinstance(e, Str):
        return q(e)
    if isinstance(e, float):
        s = ("%.4f" % e).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(e)


def find(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]


def find1(e, key):
    r = find(e, key)
    return r[0] if r else None
