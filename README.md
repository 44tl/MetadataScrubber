# MetadataScrubber

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/e5aee62d-9a0e-4b26-9b67-2df93f166b28" />

A terminal-based metadata scrubber for images, PDFs, and DOCX files. Fresh removes hidden metadata from files through an interactive TUI built with Textual.

## Features

- Interactive file browser with keyboard controls.
- Atomic file writes to avoid corruption.
- Scrubs images, PDFs, and Word documents.
- Confirmation before overwriting files.
- Minimal dependencies.

## Changelog

See the latest updates and release notes in the [Changelog](changelog.md)

## Supported Formats

| Type  | Extensions |
|-------|-----------|
| Image | `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.bmp`, `.gif` |
| PDF   | `.pdf` |
| Word  | `.docx` |

## Installation

```bash
pip3 install textual pillow pypdf python-docx
```

The script runs on Linux and macOS with Python 3.9 or newer.

> Note: `pillow`, `pypdf`, and `python-docx` are optional. If a required package is missing, supported files are listed but will fail with a message naming the missing package.

## Usage

```bash
python metadata.py
```

To start in a specific directory:

```bash
python metadata.py /path/to/files
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
