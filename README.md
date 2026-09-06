<p align="center">
  <img src="assets/CCD.ico" alt="CC Decrypter app icon" width="96" height="96">
</p>

# CC Decrypter

CC Decrypter helps you turn supported CC video files into normal MP4 files that
you can open in your usual video apps.

If a CC video file from your local draft or cache folder will not play properly,
this app can try to decrypt it and save a new playable copy. Your original file
is not changed.

Please only use CC Decrypter on files you own or have permission to decrypt.

## Download

Download the latest version from the GitHub Releases page.

Choose the file that matches your computer:

- Apple Silicon Mac: for M1, M2, M3, or newer Macs.
- Intel Mac: for older Intel-based Macs.
- Windows: for Windows 64-bit PCs.

The app is currently unsigned, so your computer may show a warning the first
time you open it.

## How To Use

1. Open CC Decrypter. It looks in your CapCut drafts folder automatically and
   lists the videos it can decrypt.
2. Click a video to select it. Click again to deselect. Pick as many as you
   like.
3. Click the big "Decrypt N videos" button.
4. Decrypted copies are saved to your CC Decrypter Exports folder. Click
   Change… to pick a different folder.
5. Open the new MP4 files in QuickTime, VLC, Premiere, Resolve, or another
   video app.

Handy extras:

- Each video in the list shows the project it belongs to and the date it was
  created.
- More videos than fit? Scroll the list with your mouse wheel or trackpad, drag
  the scrollbar on the right, or use the arrow and Page Up/Down keys.
- Not the right folder? Click Choose… (or the folder path itself) at the top
  to pick another one — CC Decrypter remembers your choice for next time.
- Prefer dark? Use the sun/moon switch at the top right — click the sun for
  light, the moon for dark. CC Decrypter follows your system appearance the
  first time you open it, then remembers your choice.
- Have a single file? Click "Have a single file? Browse…" at the bottom.
- Click "View log" to see what the app did.

That is it. The app creates a separate decrypted copy, so you can keep the
original file as a backup. Some videos take longer than others — a few can
take several minutes while the app works out how they were protected.

## What To Expect

CC Decrypter works with supported CC video files from local draft/cache folders.
It is not a general video converter, and it may not work on every file.

If the app cannot decrypt your video, keep the original file and share the error
message when reporting the issue.

## Notes

- The Apple Silicon Mac version is the recommended Mac version when possible.
- The Intel Mac version may not work perfectly on every Intel Mac yet.
- The Windows version has not been manually tested yet. If you try it, feedback
  is very welcome.

## For Developers

Run the app from source:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m cc_decrypter.app
```

Build locally:

```bash
python -m pip install pyinstaller
pyinstaller --windowed --name "CC Decrypter" --paths src src/cc_decrypter/app.py
```
