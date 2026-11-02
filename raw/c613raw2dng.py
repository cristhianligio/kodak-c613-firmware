#!/usr/bin/env python3
"""Convert Kodak EasyShare C613 'SaveCFAonTake' sensor dumps (CCDIxxxx.RAW) to DNG.

Format (reverse-engineered from firmware 1.04 + sample files):
  * no header, 2864 x 2152 pixels, 1 byte per pixel (6,163,328 bytes)
  * Bayer CFA, RGGB (row 0: R G R G..., row 1: G B G B...)
  * values are already gamma-compressed by the camera (~sRGB curve); black ~0, white 255
  * columns 0-1 are masked (optical black) pixels

Usage:  python3 c613raw2dng.py CCDI8610.RAW [more files...]   -> CCDI8610.dng
Only the Python 3 standard library is needed.
"""
import struct, sys, os, datetime

W, H = 2864, 2152
ACTIVE = (0, 2, 2152, 2864)            # top, left, bottom, right (skips masked columns)
CROP_ORIGIN = (15, 12)                 # x, y inside active area -> 2832 x 2128 like the JPEG
CROP_SIZE = (2832, 2128)

# Colour data fitted against the camera's own JPEG (D65-ish approximation).
COLOR_MATRIX = [[1.6658, -1.0808, -0.0586],
                [-1.2760, 2.1233, 0.0822],
                [0.2684, -0.3870, 0.7129]]
AS_SHOT_NEUTRAL = [0.4387, 1.0, 0.6443]   # default white balance (daylight); adjust in your editor


def srgb_to_linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


LIN_TABLE = [round(srgb_to_linear(i / 255.0) * 65535) for i in range(256)]


class Tiff:
    TYPES = {'BYTE': (1, 'B'), 'ASCII': (2, 'B'), 'SHORT': (3, 'H'), 'LONG': (4, 'I'),
             'RATIONAL': (5, 'II'), 'SRATIONAL': (10, 'ii')}

    def __init__(self):
        self.tags = []

    def add(self, tag, typ, values):
        if typ == 'ASCII':
            values = list(values.encode('ascii') + b'\0')
        self.tags.append((tag, typ, values))

    def build(self, image):
        self.tags.sort()
        n = len(self.tags)
        ifd_off = 8
        data_off = ifd_off + 2 + n * 12 + 4
        extra = bytearray()
        entries = bytearray()
        strip_fix = None
        for tag, typ, vals in self.tags:
            code, fmt = self.TYPES[typ]
            if typ in ('RATIONAL', 'SRATIONAL'):
                payload = b''.join(struct.pack('<' + fmt, *v) for v in vals)
                count = len(vals)
            else:
                payload = struct.pack('<%d%s' % (len(vals), fmt), *vals)
                count = len(vals)
            if tag == 273:              # StripOffsets placeholder
                strip_fix = len(entries) + 8
            if len(payload) <= 4:
                entries += struct.pack('<HHI', tag, code, count) + payload.ljust(4, b'\0')
            else:
                if len(extra) % 2:
                    extra += b'\0'
                entries += struct.pack('<HHII', tag, code, count, data_off + len(extra))
                extra += payload
        img_off = data_off + len(extra)
        img_off += img_off % 2
        struct.pack_into('<I', entries, strip_fix, img_off)
        out = bytearray(b'II*\0' + struct.pack('<I', ifd_off))
        out += struct.pack('<H', n) + entries + struct.pack('<I', 0) + extra
        out += b'\0' * (img_off - len(out))
        out += image
        return bytes(out)


def rational(x, den=10000):
    return (int(round(x * den)), den)


def convert(path):
    raw = open(path, 'rb').read()
    if len(raw) != W * H:
        raise ValueError(f'{path}: expected {W*H} bytes, got {len(raw)}')
    t = Tiff()
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y:%m:%d %H:%M:%S')
    t.add(254, 'LONG', [0])                        # NewSubFileType: main image
    t.add(256, 'LONG', [W]); t.add(257, 'LONG', [H])
    t.add(258, 'SHORT', [8]); t.add(259, 'SHORT', [1])
    t.add(262, 'SHORT', [32803])                   # Photometric: CFA
    t.add(271, 'ASCII', 'Eastman Kodak Company')
    t.add(272, 'ASCII', 'KODAK EASYSHARE C613 ZOOM DIGITAL CAMERA')
    t.add(273, 'LONG', [0])                        # StripOffsets (patched)
    t.add(274, 'SHORT', [1]); t.add(277, 'SHORT', [1])
    t.add(278, 'LONG', [H]); t.add(279, 'LONG', [W * H])
    t.add(284, 'SHORT', [1])
    t.add(305, 'ASCII', 'c613raw2dng 1.0')
    t.add(306, 'ASCII', mtime)
    t.add(33421, 'SHORT', [2, 2])                  # CFARepeatPatternDim
    t.add(33422, 'BYTE', [0, 1, 1, 2])             # CFAPattern RGGB
    t.add(50706, 'BYTE', [1, 4, 0, 0])             # DNGVersion
    t.add(50707, 'BYTE', [1, 1, 0, 0])             # DNGBackwardVersion
    t.add(50708, 'ASCII', 'Kodak EasyShare C613')  # UniqueCameraModel
    t.add(50710, 'BYTE', [0, 1, 2])                # CFAPlaneColor
    t.add(50711, 'SHORT', [1])                     # CFALayout rectangular
    t.add(50712, 'SHORT', LIN_TABLE)               # LinearizationTable
    t.add(50714, 'LONG', [0])                      # BlackLevel (after linearization)
    t.add(50717, 'LONG', [65535])                  # WhiteLevel
    t.add(50719, 'LONG', list(CROP_ORIGIN))        # DefaultCropOrigin
    t.add(50720, 'LONG', list(CROP_SIZE))          # DefaultCropSize
    t.add(50721, 'SRATIONAL', [rational(v) for row in COLOR_MATRIX for v in row])
    t.add(50728, 'RATIONAL', [rational(v) for v in AS_SHOT_NEUTRAL])
    t.add(50778, 'SHORT', [21])                    # CalibrationIlluminant1 = D65
    t.add(50829, 'LONG', list(ACTIVE))             # ActiveArea
    out = os.path.splitext(path)[0] + '.dng'
    open(out, 'wb').write(t.build(raw))
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        print(p, '->', convert(p))
