# CC Video Repair

Private desktop utility for repairing authorized local editor draft video files.

This project provides a small Tkinter app and CLI-style Python API. It detects a
BDVE-protected MP4 resource, derives the XOR cryptor tuple from the file itself,
strips the BDVE footer, and writes a playable MP4.

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m cc_video_repair.app
```

## Build Locally

```bash
python -m pip install pyinstaller
pyinstaller --windowed --name "CC Video Repair" --paths src src/cc_video_repair/app.py
```

On macOS universal builds:

```bash
pyinstaller --windowed --name "CC Video Repair" --target-arch universal2 --paths src src/cc_video_repair/app.py
```

## GitHub Actions

The workflow in `.github/workflows/build.yml` builds unsigned artifacts for:

- macOS Intel `.dmg`
- macOS Apple Silicon `.dmg`
- Windows x64 Inno Setup `.exe` installer

Manual build:

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Run **Build desktop apps**.

Tag build:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Tag builds attach both installer files to a GitHub Release. Unsigned apps may
show operating-system trust warnings. Signing and notarization can be added
later.
