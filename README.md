# CC Video Repair

CC Video Repair is a small desktop app for recovering your own local editor
draft video files when they are stuck in a protected cache format and will not
play normally.

Drop in the affected video file, choose where to save the repaired copy, and the
app writes a normal MP4 you can try opening in QuickTime, VLC, Premiere,
Resolve, or another video tool.

This tool is meant only for files you own or are authorized to repair.

## Download

Go to the latest GitHub Release and download the installer for your computer:

- Apple Silicon Mac: use the Apple Silicon DMG if your Mac has an M1, M2, M3,
  or newer Apple chip.
- Intel Mac: use the Intel DMG if your Mac uses an Intel processor.
- Windows: use the Windows x64 Setup file.

The apps are currently unsigned, so macOS or Windows may show a security
warning the first time you open them.

## How To Use

1. Open CC Video Repair.
2. Select the damaged or protected local video file.
3. Choose a save location for the repaired MP4.
4. Click Decode.
5. Open the new MP4 in your video player or editor.

The original file is left untouched. The app writes a separate repaired copy.

## What It Can Repair

CC Video Repair is designed for supported BDVE-protected MP4 draft/cache files.
It may not repair every damaged video. If the app cannot read the file, try
keeping a copy of the original file and share the error message when reporting
the issue.

## Run From Source

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m cc_video_repair.app
```

## Build From Source

```bash
python -m pip install pyinstaller
pyinstaller --windowed --name "CC Video Repair" --paths src src/cc_video_repair/app.py
```

On macOS builds:

```bash
pyinstaller --windowed --name "CC Video Repair" --icon assets/CCD.icns --osx-bundle-identifier com.xorica.ccvideorepair --paths src src/cc_video_repair/app.py
```

## Release Builds

The workflow in `.github/workflows/build.yml` builds unsigned artifacts for:

- macOS Intel `.dmg`
- macOS Apple Silicon `.dmg`
- Windows x64 Inno Setup `.exe` installer

To build manually from GitHub:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Run **Build desktop apps**.

To publish a release, push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Tag builds attach the installer files to a GitHub Release.
