#!/usr/bin/env python3
"""Annotated word dump of section 1 (menu resources), resolving string IDs,
pointers into section 1 and code addresses.

Usage: python3 menudump.py seg1.bin seg3.bin START END   (offsets in hex, e.g. 2a80c 2aa60)
"""
import struct, sys

SEG1_BASE, SEG0_BASE, SEG0_END = 0x15C000, 0x30000, 0x15B600


def english(seg3):
    base = 4 + 831 * 4
    offs = struct.unpack_from('<831I', seg3, 4)
    return [seg3[base + o:seg3.find(b'\0', base + o)].decode('latin-1') for o in offs]


def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    s1 = open(sys.argv[1], 'rb').read()
    en = english(open(sys.argv[2], 'rb').read())
    lo, hi = int(sys.argv[3], 16), int(sys.argv[4], 16)
    for o in range(lo, hi, 4):
        w = struct.unpack_from('<I', s1, o)[0]
        note = ''
        if 0 < w < len(en):
            note = f'str#{w} {en[w][:30]!r}'
        elif SEG1_BASE <= w < SEG1_BASE + len(s1):
            p = w - SEG1_BASE
            t = s1[p:s1.find(b'\0', p)]
            note = f'ptr "{t.decode()}"' if 1 < len(t) < 32 and all(32 <= c < 127 for c in t) else f'ptr seg1+{p:#x}'
        elif SEG0_BASE <= w < SEG0_END:
            note = f'code RAM {w:#x}'
        print(f'{o:#07x} RAM {SEG1_BASE + o:#08x}  {w:#010x}  {note}')


if __name__ == '__main__':
    main()
