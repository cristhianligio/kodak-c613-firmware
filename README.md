# Kodak EasyShare C613 firmware research

Community fixes and tools for the **Kodak EasyShare C613** (2007), which Kodak no longer supports.

| | Status |
|---|---|
| **Date fix**: Kodak's firmware only allows years 2006–2025. The patched firmware allows up to 2037. | ✅ Tested on a real camera |
| **RAW → DNG**: converts the camera's hidden sensor-RAW files to DNG | ✅ Working, wider testing welcome |
| **RAW menu**: a normal "RAW: OFF/ON" item in the Capture menu | 🚧 In progress |

No Kodak files are included. The scripts patch or read **your own copy** of Kodak's update.

## 1. Fix the 2025 date limit

1. Download Kodak's official C613 firmware 1.04 update, **`KC613104.exe`**. Kodak's site is
   gone, but it's still mirrored (search for `KC613104.exe`).
2. Build the patched firmware (Python 3, no extra packages):
   ```
   python3 firmware/patch_c613.py KC613104.exe KC613.FW
   ```
   The script verifies the input (SHA-256 `2c1308f9…a998` for `kc613.fw`). The output
   should report `matches the build tested on a real camera: True`.
3. Put fresh batteries in the camera.
4. On an SD card formatted in the camera, create a folder named **`SYSTEM`** at the root and copy
   `KC613.FW` into it.
5. Insert the card and switch on. The camera finds the file and updates itself, and the file is
   renamed `KC613.OLD`.
6. Set the date: the year can now go up to 2037.

> ⚠️ Flashing firmware is at your own risk. Don't remove power during the update.

If you'd rather not flash: 2026 has the same calendar as 2015. Set the camera to 2015 and shift the
photo dates afterwards with
`exiftool "-AllDates+=11:0:0 0:0:0" -overwrite_original <folder>`.

## 2. Take RAW photos and convert them

1. Open Setup → About, then hold **Delete + Right** to open the hidden menu.
2. Choose **Debug** → **SaveCFAonTake** → **On**. This resets at every power-on.
3. Each photo now also produces a `CCDIxxxx.RAW` file (2864×2152, 8-bit, RGGB).
4. Convert it:
   ```
   python3 raw/c613raw2dng.py CCDIxxxx.RAW
   ```

Ignore the "YRGB" option mentioned on forums. It saves the already-processed image, not sensor data.

## Repository layout

```
firmware/patch_c613.py              date-limit patch (input: KC613104.exe or kc613.fw)
raw/c613raw2dng.py                  CCDIxxxx.RAW -> DNG converter
docs/firmware-format-and-date-fix.md  container format, checksums, how the clock works
docs/raw-capture.md                 hidden menus, RAW format, Capture-menu research
tools/fwinfo.py                     section table, checksum check, section extraction
tools/langstrings.py                dump the 19-language string table (section 3)
tools/menudump.py                   annotated dump of menu resources (section 1)
```

## How it was done

The firmware is ARCompact (ARC 600/700) code in a custom `RHIR` container with 32-bit
word-sum checksums. It was disassembled with radare2 and analysed statically. See `docs/`
for details and addresses.

## License

The scripts and documentation are released under the [MIT License](LICENSE).

## Disclaimer

This is an unofficial project, not affiliated with or endorsed by Eastman Kodak Company.
"Kodak" and "EasyShare" are trademarks of their owner. Use at your own risk.
