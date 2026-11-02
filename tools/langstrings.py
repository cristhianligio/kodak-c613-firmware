#!/usr/bin/env python3
"""Dump the multi-language string table (section 3 of the C613 firmware).

Each language block: u32 magic 0x3BD12791, 831 u32 offsets, NUL-terminated strings.
Usage: python3 langstrings.py seg3.bin [block_index]   (0 = English, 3 = Spanish)
"""
import struct, sys

MAGIC = struct.pack('<I', 0x3BD12791)
COUNT = 831


def blocks(s):
    i = s.find(MAGIC)
    while i >= 0:
        yield i
        i = s.find(MAGIC, i + 1)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    s = open(sys.argv[1], 'rb').read()
    bl = list(blocks(s))
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = bl[idx]
    base = b + 4 + COUNT * 4
    offs = struct.unpack_from('<%dI' % COUNT, s, b + 4)
    print(f'{len(bl)} language blocks; showing #{idx} at {b:#x}')
    for n, o in enumerate(offs):
        p = base + o
        text = s[p:s.find(b'\0', p)].decode('latin-1')
        print(f'{n:4d} {text!r}')


if __name__ == '__main__':
    main()
