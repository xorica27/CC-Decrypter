# Changelog

All notable changes to CC Decrypter are documented here. Download the latest
version from the GitHub Releases page.

## 0.2.1 — 2026-09-06

- Fixed: the video list would not scroll. The mouse wheel and trackpad now
  scroll the list from anywhere in the window, a slim scrollbar shows where you
  are in a long list and can be dragged, and the arrow, Page Up/Down, Home, and
  End keys scroll too.
- The light/dark switch is now a proper two-segment control — a sun half and a
  moon half, with the current one highlighted — instead of a bare icon. Click a
  half to pick that appearance.
- The mouse pointer no longer changes into a hand over buttons and links; it
  stays the normal arrow everywhere in the main window.

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
