# Firmware format and the date-limit fix

Firmware analysed: Kodak EasyShare C613 **1.04** (shown on the camera as "1.4"), the only update Kodak published.

## 1. The official update file

- `KC613104.exe` is a WinZip self-extractor; inside is `kc613.fw` (2,419,712 bytes,
  SHA-256 `2c1308f9e343f14dddba165b1071d7a1a224b89a6add87e7d6dfed6fa6fda998`).
- The camera looks for the update at `B:\SYSTEM\KC613.FW` (B: = SD card) or `A:\KC613.FW`
  (internal memory). After a successful update it renames the file to `KC613.OLD`.
- **Verified install method:** create a `SYSTEM` folder at the root of the SD card, put
  `KC613.FW` in it, insert the card and switch on — the update starts automatically.
- Manual path: Setup → About, hold **Delete + Right** → hidden menu → *Update Firmware*.

## 2. Container format ("RHIR", 512-byte sectors)

| Offset | Meaning |
|---|---|
| 0x00 | magic `RHIR` |
| 0x06 | number of sections |
| 0x08 | `word & 0x00FFFF00` must be `0x00034000` (model ID) |
| 0x10 | section table, 16 bytes each: `u16 flag, u16 start sector, u16 sector count, u32 load address, u32 checksum` |
| 0x1F0 | `KHIR`, then `u32` word-sum of header bytes 0..0x1EF, then an unidentified `u32` |

- Checksum = 32-bit sum of little-endian words over the whole section. The camera
  (routine at RAM 0x137BD0) checks only sections with flag = 1.
- Because the word at 0x1F8 is not understood, the patch **never changes the header**.

| # | flag | load address | contents |
|---|---|---|---|
| 0 | 1 | 0x30000 | ARCompact (ARC 600/700) code |
| 1 | 1 | 0x15C000 | initialised data, menu resources (also contains a SPARC co-processor blob) |
| 2 | 0 | 0x1DC000 | data |
| 3 | 0 | 0x22C200 | language strings (19 languages) |
| 4 | 1 | 0x22C200 | font / bitmap data |

The boot loader (flash 0–0x30000) is not part of the update file and is never touched.

## 3. How the clock works

- The date is kept as a C `struct tm` (`tm_year` = year − 1900).
- The RTC is a 64-bit 32.768 kHz tick counter converted to days + seconds since a stored base
  date using plain Gregorian arithmetic: no year tables and no 2038 overflow.
- The 2006–2025 limit exists in exactly three places:
  - set-time validator (RAM 0x07B15E) – rejects years outside the range;
  - date/time screen #1 (RAM 0x0FDE52) and screen #2 (RAM 0x110366) – wrap >2025 → 2006 and <2006 → 2025.

## 4. The patch (`firmware/patch_c613.py`)

- Raises the upper limit to 2037 (configurable up to 2099): 5 instruction changes, 7 bytes.
  2037 matches Kodak's own C813 and stays clear of 32-bit timestamps elsewhere
  (e.g. QuickTime movie headers overflow in 2040).
- A compensating word in unused padding at the end of section 0 keeps the section checksum
  unchanged, so the header and sections 1–4 are byte-identical to Kodak's file.
- Output SHA-256 for 2037: `8a0b69796633f5bc7368572532cb52157d4e6c2b12ff10fb767ffc1e243bceae`.
- **Tested on a real camera (2026-10-30):** update applied, year 2026 can be set.

## 5. Workaround without flashing

2026 has the same calendar as 2015 (Thursday 1 January, not a leap year). Set the camera to
2015 and fix the photo dates afterwards:

```
exiftool "-AllDates+=11:0:0 0:0:0" -overwrite_original <folder>
```
