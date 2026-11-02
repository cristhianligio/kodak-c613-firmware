#!/usr/bin/env python3
"""Show the RHIR section table of a Kodak C613 firmware image, verify the
checksums the camera checks, and optionally extract each section.

Usage: python3 fwinfo.py kc613.fw [outdir]
"""
import os, struct, sys


def s32(b):
    return sum(struct.unpack('<%dI' % (len(b) // 4), b)) & 0xFFFFFFFF


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = open(sys.argv[1], 'rb').read()
    out = sys.argv[2] if len(sys.argv) > 2 else None
    assert d[:4] == b'RHIR', 'not an RHIR firmware image'
    n = d[6]
    print(f'size {len(d)} bytes, {n} table entries, model word {struct.unpack_from("<I", d, 8)[0]:#010x}')
    print(f'header sum @0x1F4 {struct.unpack_from("<I", d, 0x1F4)[0]:#010x} (calc {s32(d[:0x1F0]):#010x})')
    for i in range(n):
        fl, st, cnt, addr, ck = struct.unpack_from('<HxxHHII', d, 0x10 + i * 16)
        if cnt == 0:
            continue
        seg = d[st * 512:(st + cnt) * 512]
        ok = 'ok' if s32(seg) == ck else ('MISMATCH' if fl == 1 else 'not checked')
        print(f'#{i} flag={fl} file_off={st*512:#09x} len={cnt*512:#08x} load={addr:#08x} sum={ck:#010x} {ok}')
        if out:
            os.makedirs(out, exist_ok=True)
            open(os.path.join(out, f'seg{i}.bin'), 'wb').write(seg)


if __name__ == '__main__':
    main()
