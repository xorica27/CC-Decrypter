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

1. Open CC Decrypter.
2. Click Browse next to the input field.
3. Choose the CC video file you want to decrypt.
4. Choose where to save the new MP4 file.
5. Click Decode.
6. Wait until the app finishes.
7. Open the new MP4 in QuickTime, VLC, Premiere, Resolve, or another video app.

That is it. The app creates a separate decrypted copy, so you can keep the
original file as a backup.

## What To Expect

CC Decrypter works with supported CC video files from local draft/cache folders.
It is not a general video repair tool, and it may not work on every file.

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
PYTHONPATH=src python -m cc_video_repair.app
```

Build locally:

```bash
python -m pip install pyinstaller
pyinstaller --windowed --name "CC Decrypter" --paths src src/cc_video_repair/app.py
```
