# RAW capture on the C613

## Hidden menus

Setup → About, then hold **Delete + Right** to open the HIDDEN MENU: Firmware Version,
Product Information, Error Code, Calibration Data, Debug, Total info, Update Firmware, DebugMode.

The **Debug** entry opens the DEBUG MENU: SaveCFAonTake, SaveCFAonIRP, SaveThumYRGB,
SaveThumJPEG, SaveVGAYRGB, SaveVGAJPEG, SaveFullYRGB, SaveFullJPEG (default On), SaveAEOnS1.

| Option | What it saves |
|---|---|
| **SaveCFAonTake** (internal name *SaveCCDRawOnTake*) | **True sensor RAW** (colour-filter-array data) |
| SaveFullYRGB (the "YRGB" mode described on forums) | Already processed full-size YUV image — not sensor RAW, which is why Photoshop/dcraw cannot read it |

All of these switches are plain RAM variables and **reset at every power-on**:

- flag structure at RAM 0x15EBEC (`+11` CFA-on-IRP, `+12..+17` Thumb/VGA/Full YRGB/JPEG);
- SaveCFAonTake byte at RAM 0x15EEB8 (getter at RAM 0x7255C, setter at RAM 0x72568).

## RAW file format (`CCDIxxxx.RAW`)

Decoded from a real sample (verified on camera, one `.RAW` per shot next to the JPEG):

- 6,163,328 bytes = **2864 × 2152 pixels, 1 byte per pixel**, no header;
- Bayer pattern **RGGB**;
- 8-bit values already gamma-compressed by the camera (close to the sRGB curve);
  black ≈ 0, white = 255; columns 0–1 are masked (optical black).

Because the data are 8-bit and gamma-encoded, the RAW does not recover more highlight or
shadow detail than the JPEG. Its advantages: no JPEG compression, no in-camera sharpening or
noise reduction, white balance chosen afterwards.

## DNG converter (`raw/c613raw2dng.py`)

```
python3 raw/c613raw2dng.py CCDI8610.RAW      # -> CCDI8610.dng
```

Python 3 standard library only. Writes DNG 1.4 with CFA pattern RGGB, a linearization
table (inverse sRGB → 16-bit), active area skipping the masked columns, default crop
2832 × 2128 (same as the JPEG) and a colour matrix fitted against the camera's own JPEG.
Checked by parsing and by developing the DNG from its own tags; please report results from
Lightroom / Photoshop / darktable / RawTherapee.

## Work in progress: a "RAW" item in the Capture menu

Goal: a normal **RAW: OFF / ON** entry in the Capture menu (English and Spanish), reset to
OFF at power-on.

Findings so far (static analysis, nothing flashed yet):

- **Strings** (section 3): 19 language blocks, 512-byte aligned, magic `0x3BD12791`,
  831 `u32` offsets then NUL-terminated strings. IDs 173/174 are OFF/ON in every language.
- **Capture menu** (section 1, RAM = 0x15C000 + offset): 11 items × 24 bytes at 0x2A80C:
  `[u16 icon, u16 icon] [ptr value text] [title string ID] [0] [help ID] [0]`.
  Item count byte at 0x2A930, list pointer at 0x2A94C. Selecting item *n* raises event
  `0x5000 + n`, dispatched through the resource's event table.
- **Free space**: a 208-byte block of USB string descriptors is duplicated 239 times in
  section 1; 190 copies (~41 KB) are never referenced, including one directly before the
  Capture item list, so the list can grow in place. Plus ~460 bytes of padding at the end
  of section 0.
- Planned prototype: add the item before SETUP MENU, hook the event table's default
  handler for the new event, small OFF/ON sub-menu calling the existing RAW setter.
