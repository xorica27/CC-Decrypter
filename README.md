<p align="center">
  <img src="assets/CCD.ico" alt="CC Decrypter app icon" width="96" height="96">
</p>

# CC Decrypter

CC Decrypter makes protected videos from your CapCut drafts playable again.

Videos you edit in CapCut are sometimes saved in a protected format. They will
not open in QuickTime, VLC, Premiere, or other apps. CC Decrypter finds those
videos on your computer, turns them into normal MP4 files, and saves them in a
folder you choose.

Your original videos are never changed — CC Decrypter always creates a new
copy.

Please only use CC Decrypter on videos you own or have permission to decrypt.

## Download and Install

1. Open the [latest release page](https://github.com/xorica27/CC-Decrypter/releases/latest).
2. Download the file for your computer:

   | Your computer | File to download |
   | --- | --- |
   | Mac with M1, M2, M3, or newer chip | `CC-Decrypter-macOS-Apple-Silicon.dmg` |
   | Older Intel Mac | `CC-Decrypter-macOS-Intel.dmg` |
   | Windows 64-bit PC | `CC-Decrypter-Windows-x64-Setup.exe` |

   Both Mac versions need macOS 12 or newer.

3. Install the app:
   - **Mac:** open the downloaded DMG file and drag **CC Decrypter** into your
     Applications folder.
   - **Windows:** run the downloaded Setup file.

### Opening the app the first time

CC Decrypter is unsigned, so your computer may ask for confirmation the first
time you open it. This is normal for apps without a paid security certificate,
and you only need to confirm once.

- **Mac:** if your Mac says the app cannot be opened, right-click (or
  Control-click) CC Decrypter in Applications, choose **Open**, then choose
  **Open** again. You can also go to System Settings → Privacy & Security and
  click **Open Anyway**.
- **Windows:** if a SmartScreen warning appears, click **More info**, then
  **Run anyway**.

## How to Use CC Decrypter

### Step 1: Open the app

CC Decrypter looks in your CapCut drafts folder by itself and lists the videos
it can decrypt. Each row shows the video name, the project it belongs to, the
date it was created, and how big it is.

### Step 2: Pick your videos

Click a video to select it — a blue check mark appears. Click it again to
remove it. You can pick as many videos as you like, drag over several at once,
or hold Shift to take a whole run of them.

The line under the list shows how many videos you selected and their total
size.

### Step 3: Click the decrypt button

Press the big blue button. It says **Decrypt 3 videos** (or however many you
picked).

A progress bar shows how far along it is and which video it is working on, and
**Cancel** stops after the video in flight. When it is done you will see
**Last run: 3 decrypted · 0 failed** at the bottom of the window, and the
finished message offers **Show in Finder**.

### Step 4: Watch your videos

Open the new MP4 files in QuickTime, VLC, Premiere, Resolve, or any other
video app. They are normal video files now.

## Helpful Extras

- **Sort the list.** Use **Date / Name / Size** above the list. Click the same
  one again to flip the order. CC Decrypter remembers how you like it sorted.
- **Move through the list.** Scroll with your trackpad or mouse, use the arrow
  keys, Page Up/Down or Home/End, or start typing a filename to jump to it.
- **Your videos are somewhere else?** Click **Choose…** at the top and pick
  any folder. CC Decrypter remembers your choice for next time. Click
  **Rescan** to refresh the list.
- **Added new videos in CapCut?** Click **Rescan** and they will appear.
- **Already decrypted something?** Those videos are marked **exported**, and if
  you pick them again CC Decrypter offers to skip them instead of making a
  second copy.
- **Open your exports.** Click the **Saved to** path at the bottom to open that
  folder.
- **Prefer dark?** Use the sun/moon switch at the top right. The app matches
  your computer's appearance until you pick one, then remembers your choice.
- **Want to see what the app is doing?** Click **View log** at the bottom.
- **Which version am I running?** Click **About** at the bottom. It also has a
  **Check for updates** button and a **Copy details** button for bug reports.
- **Keyboard:** Cmd/Ctrl+R rescans, Cmd/Ctrl+A selects everything,
  Cmd/Ctrl+Return starts decrypting, Cmd/Ctrl+L opens the log.

## Questions and Answers

**I do not see my video in the list. Why?**
The list only shows videos that are still protected. If a video already plays
normally in other apps, it does not need decrypting, so it is not listed.

**One or more videos failed. What now?**
Open **View log** to see what went wrong, and keep the original file. A few
videos use a protection that CC Decrypter cannot unlock yet.

**A video is taking a very long time. Is it stuck?**
Probably not. Some videos take several minutes while CC Decrypter works out
how they were protected. The progress bar names the video it is working on, and
**View log** shows it working.

**Where are my decrypted videos?**
In the **CC Decrypter Exports** folder in your home folder, unless you picked
somewhere else with **Change…** — that choice is remembered too. Click the
**Saved to** path to open the folder. Files that already exist are never
overwritten; you always get a fresh copy.

**CC Decrypter did not find my CapCut folder.**
Click **Choose…** and point it at your drafts folder. It looks in the usual
places for the CapCut and JianyingPro apps, including the sandboxed Mac App
Store version, but a custom install can live anywhere. If a folder you picked
before goes missing, the app says so rather than quietly scanning elsewhere.

**Does CC Decrypter change my original videos?**
No. It only reads them and writes a new, separate file.

**Can it convert any video?**
No. CC Decrypter only decrypts protected draft videos it supports. It is not a
general video converter.

## Notes

- The app is notarization-free (unsigned), so the first-open warning described
  above is expected.
- If a video cannot be decrypted, your original file is still safe. Please
  share the error message from **View log**, and the details from **About**,
  when asking for help.
- Only use CC Decrypter on videos you made yourself or have permission to
  decrypt.

## For Developers

Run the app from source:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m cc_decrypter.app
```

Run the tests (they use Qt's offscreen platform, so no window appears):

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

Build locally:

```bash
python -m pip install pyinstaller
pyinstaller --windowed --name "CC Decrypter" --paths src src/cc_decrypter/app.py
```
