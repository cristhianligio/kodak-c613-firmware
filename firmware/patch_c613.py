#!/usr/bin/env python3
"""Patch Kodak EasyShare C613 firmware 1.04 so the clock accepts years 2006-2037.

Kodak's firmware only lets you pick 2006-2025. This script rebuilds the official
1.04 image with a higher upper limit. It does not contain any Kodak code: you
supply Kodak's own update file.

Usage:
    python3 patch_c613.py KC613104.exe KC613.FW [maxyear]
    python3 patch_c613.py kc613.fw     KC613.FW [maxyear]

Input:  Kodak's KC613104.exe (self-extracting zip) or the kc613.fw inside it.
Output: KC613.FW - copy it to a folder named SYSTEM on the SD card, insert the
        card and switch the camera on; it updates automatically.

maxyear defaults to 2037 (avoids 32-bit timestamp limits elsewhere).
Only Python 3 standard library is required.
"""
import hashlib
import io
import struct
import sys
import zipfile

SRC_SHA256 = '2c1308f9e343f14dddba165b1071d7a1a224b89a6add87e7d6dfed6fa6fda998'
OUT_SHA256_2037 = '8a0b69796633f5bc7368572532cb52157d4e6c2b12ff10fb767ffc1e243bceae'

SEG0_FILE_OFF = 0x200          # section 0 starts at sector 1
SEG0_LEN = 0x12B600
SEG0_SUM_FIELD = 0x10 + 12     # checksum of section 0 in header table
COMP_OFF = 0x12B5FC            # last word of section-0 padding (unused)


def s32(b):
    return sum(struct.unpack('<%dI' % (len(b) // 4), b)) & 0xFFFFFFFF


def cmp_s12(reg, val):
    """ARCompact 'cmp rB, s12' (b<8, F=1)."""
    hi, lo = (val >> 6) & 0x3F, val & 0x3F
    w1 = 0x208C | (reg << 8)             # major 4, P=10, op CMP
    w2 = 0x8000 | (lo << 6) | hi
    return struct.pack('<HH', w1, w2)


def mov_s_u8(reg, val):
    return struct.pack('<H', 0xD800 | (reg << 8) | val)


def load_source(path):
    data = open(path, 'rb').read()
    if data[:2] == b'MZ':                       # Kodak's self-extracting .exe
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next(n for n in z.namelist() if n.lower() == 'kc613.fw')
            data = z.read(name)
    return bytearray(data)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    maxyear = int(sys.argv[3]) if len(sys.argv) > 3 else 2037
    if not 2026 <= maxyear <= 2099:
        sys.exit('maxyear must be between 2026 and 2099')

    d = load_source(src)
    sha = hashlib.sha256(d).hexdigest()
    if sha != SRC_SHA256:
        sys.exit(f'Unexpected input (sha256 {sha}).\n'
                 'This patch only applies to the official C613 firmware 1.04 (kc613.fw).')

    seg = bytearray(d[SEG0_FILE_OFF:SEG0_FILE_OFF + SEG0_LEN])
    want_sum = struct.unpack_from('<I', d, SEG0_SUM_FIELD)[0]
    assert s32(seg) == want_sum, 'section 0 checksum mismatch in source'

    patches = [
        # (section-0 offset, original bytes, new bytes, description)
        (0x4B164, cmp_s12(0, 2025), cmp_s12(0, maxyear), 'date validator: year <= MAX'),
        (0xCDE60, cmp_s12(1, 2025), cmp_s12(1, maxyear), 'date screen #1: wrap above MAX'),
        (0xCDE5A, mov_s_u8(0, 125), mov_s_u8(0, maxyear - 1900), 'date screen #1: wrap below 2006 -> MAX'),
        (0xE0374, cmp_s12(1, 2025), cmp_s12(1, maxyear), 'date screen #2: wrap above MAX'),
        (0xE036E, mov_s_u8(0, 125), mov_s_u8(0, maxyear - 1900), 'date screen #2: wrap below 2006 -> MAX'),
    ]
    for off, old, new, desc in patches:
        cur = bytes(seg[off:off + len(old)])
        assert cur == old, f'{desc}: expected {old.hex()} got {cur.hex()} @ {off:#x}'
        seg[off:off + len(new)] = new
        print(f'  section0+{off:#08x} (RAM {off + 0x30000:#08x}) {old.hex()} -> {new.hex()}  {desc}')

    # Keep the header untouched: compensate the word-sum in unused padding.
    assert seg[COMP_OFF:COMP_OFF + 4] == b'\0\0\0\0'
    comp = (want_sum - s32(seg)) & 0xFFFFFFFF
    seg[COMP_OFF:COMP_OFF + 4] = struct.pack('<I', comp)
    assert s32(seg) == want_sum
    print(f'  compensation word {comp:#010x} at section0+{COMP_OFF:#x} (padding)')

    d[SEG0_FILE_OFF:SEG0_FILE_OFF + SEG0_LEN] = seg
    open(dst, 'wb').write(d)
    out_sha = hashlib.sha256(d).hexdigest()
    print('wrote', dst, 'sha256', out_sha)
    if maxyear == 2037:
        print('matches the build tested on a real camera:', out_sha == OUT_SHA256_2037)


if __name__ == '__main__':
    main()
