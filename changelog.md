# Changelog

## 2026-08-11

- Added support for a reusable virtual environment launcher.
- Improved metadata scrubber TUI with file type and status columns.
- Added file count, selected count, and current directory info in the TUI.
- Added a scrub-all action with the `s` key and clearer help text.
- Added a simple ASCII preview panel for image files.
- Improved missing package status labels to show the required package name.
- Added directory reload and command-line directory argument.
- Switched atomic save to `os.replace` for safer file replacement on Unix.
- Added reusable shell helper for persistent Python environment activation.
