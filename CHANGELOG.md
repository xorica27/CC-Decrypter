# Changelog

All notable changes to CC Decrypter are documented here. Download the latest
version from the GitHub Releases page.

## 0.2.0 — 2026-09-04

The app got a full redesign around your CapCut drafts folder.

- New single-window flow: CC Decrypter finds the videos it can decrypt in your
  CapCut drafts folder automatically and lists them with their project,
  creation date, and size.
- Select any number of videos and decrypt them in one go. Decrypted MP4s are
  saved to one output folder with clear names and never overwrite earlier
  exports.
- Choose a different folder to scan with Choose… The app remembers your
  choice for next time.
- Dark mode: the app follows your system appearance the first time you open
  it, and you can switch any time with the moon/sun icon. Both the theme and
  the folder choice are remembered.
- The activity log and the classic single-file decrypt now live in their own
  windows to keep the main window focused.
- Under the hood: a fast scanner that reads only the tail of each file to
  detect supported videos, and it skips files that are already plain MP4.

## Earlier releases

Versions up to 0.1.14 were single-file decrypt releases with a form-based
window. Those installers remain on the GitHub Releases page.
