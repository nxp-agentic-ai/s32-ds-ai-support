# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

"""Find balanced <array name="NAME">...</array> elements in an XML string.

Naive regex breaks on nested arrays (S32CT `.mex` files have arrays nested
inside structs inside arrays, many layers deep). This helper does it
correctly, accounting for self-closing variants `<array name="X" .../>`.

Used by `splice.py` and `sanitize.py`; importable as a library.

Example:

    from balanced_array import find_balanced_named_array
    r = find_balanced_named_array(mex_text, "CanController")
    if r:
        open_pos, body_start, body_end, close_end = r
        body = mex_text[body_start:body_end]
"""
import re


def find_balanced_named_array(text, name, start_idx=0):
    """Find <array name="NAME"> ... matching </array>, with correct nesting.

    Returns (open_start, body_start, body_end, close_end) or None.
    Self-closing <array name="..." .../> elements do NOT increase depth and are
    skipped over.
    """
    open_tag = f'<array name="{name}">'
    op = text.find(open_tag, start_idx)
    if op < 0:
        return None
    body_start = op + len(open_tag)

    # Token scanner: matches both <array ...> open tags and </array> closes,
    # also recognises self-closing <array ... /> via the captured "/".
    rx = re.compile(r'<array\b[^>]*?(/?)>|</array>')
    depth = 1
    for m in rx.finditer(text, body_start):
        tok = m.group(0)
        if tok == '</array>':
            depth -= 1
            if depth == 0:
                return op, body_start, m.start(), m.end()
        elif tok.endswith('/>'):
            # self-closing array - no depth change
            continue
        else:
            depth += 1
    return None


def find_all_balanced_arrays(text):
    """Iterate all <array name="X"> elements in source order, yielding
    (name, open_start, body_start, body_end, close_end).

    Useful for systematic sweeps (sanitize.py uses this).
    """
    for m in re.finditer(r'<array name="([A-Za-z0-9_]+)">', text):
        r = find_balanced_named_array(text, m.group(1), m.start())
        if r is None:
            continue
        if r[0] != m.start():
            # An earlier opening of the same name matched first; skip this
            # iteration's start position - we'll see it via the earlier op.
            continue
        yield (m.group(1), *r)


if __name__ == "__main__":
    # Self-test
    sample = """
    <array name="Outer">
        <struct name="0">
            <array name="Inner"/>
            <array name="Inner">
                <setting name="0" value="a"/>
            </array>
        </struct>
    </array>
    """
    r = find_balanced_named_array(sample, "Outer")
    assert r, "outer not found"
    body = sample[r[1]:r[2]]
    assert "Inner" in body
    assert sample.count("</array>") == 2, "should still have 2 close tags"
    print("Self-test OK.")
