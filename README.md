# MetadataScrubber [ Version 1.1 Freshly ]

A terminal-based metadata scrubber for images, PDFs, and DOCX files. Fresh removes hidden metadata (EXIF, document info, author tags, etc.) through an interactive TUI built with Textual, using atomic writes to prevent data loss.

<img width="1876" height="967" alt="image" src="https://github.com/user-attachments/assets/6107eee8-470e-40e3-8a84-c7d50d91f577" />

## Features

- **Modern TUI**: interactive file browser built with Textual, with keyboard navigation and live status updates.
- **Atomic writes**: files are written to a temporary location and atomically replaced, protecting against corruption on failure. Original file permissions are preserved.
- **Non-blocking**: scrubbing runs off the UI thread, so the interface stays responsive on large files.
- **Confirmation before scrubbing**: scrubbing overwrites files in place, so you're asked to confirm before it runs.
- **Broad format support**: images (including animated GIFs, which keep their frames and timing), PDFs, and Word documents.
- **Minimal dependencies**: built on Pillow, pypdf, and python-docx.

## Supported Formats

| Type  | Extensions |
|-------|-----------|
| Image | `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.bmp`, `.gif` |
| PDF   | `.pdf` |
| Word  | `.docx` |

## Installation

```bash
pip install textual pillow pypdf python-docx
```

> **Note:** `pillow`, `pypdf`, and `python-docx` are each optional independently. Files of a format whose library isn't installed are still listed, but attempting to scrub them fails with an error naming the missing package.

## Usage

```bash
python metadata.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `UP` / `DOWN` | Navigate the file list |
| `SPACE` | Toggle file selection |
| `a` | Select all files |
| `d` | Deselect all files |
| `ENTER` | Scrub selected files (asks for confirmation) |
| `c` | Change working directory |
| `h` | Show help |
| `q` | Quit |

## How It Works

### Images

Opens the image, discards all metadata, and re-encodes using only the raw pixel data. This strips EXIF, IPTC, XMP, and any other embedded tags. Animated GIFs are scrubbed frame by frame, preserving frame order, duration, and loop count.

### PDFs

Copies all pages to a new PDF and clears the document information dictionary using `pypdf`.

### DOCX

Clears core properties (author, title, dates, etc.) via `python-docx`, then rewrites the ZIP archive with empty `docProps/app.xml` and `docProps/custom.xml` entries to remove extended and custom properties.

## Safety

All writes use an atomic save strategy:

1. Content is written to a temporary file in the same directory, then given the original file's permissions.
2. On success, the temporary file replaces the original in a single move.
3. On failure, the temporary file is removed and the original is left untouched.

Scrubbing is destructive and irreversible, so the app asks for confirmation before overwriting any selected files.

## Requirements

- Python 3.9+
- A modern terminal emulator (Windows Terminal, iTerm2, GNOME Terminal, etc.)
