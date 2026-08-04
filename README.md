A modern terminal-based metadata scrubber for images, PDFs, and DOCX files. Frewsh removes hidden metadata (EXIF, document info, author tags, etc.) through an interactive TUI built with Textual, featuring atomic writes to prevent data loss.

<img width="1876" height="967" alt="image" src="https://github.com/user-attachments/assets/6107eee8-470e-40e3-8a84-c7d50d91f577" />

## Features

- **Modern TUI** — Interactive file browser built with Textual, featuring keyboard navigation and real-time status updates.
- **Atomic writes** — Files are written to a temporary location and atomically replaced, protecting against corruption on failure.
- **Broad format support** — Handles common image formats, PDFs, and Word documents.
- **Minimal dependencies** — Built on Pillow, pypdf, and python-docx.

## Supported Formats

| Type | Extensions |
|------|-----------|
| Image | `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`, `.bmp`, `.gif` |
| PDF | `.pdf` |
| Word | `.docx` |

## Installation

```bash
pip install textual pillow pypdf python-docx
```

> **Note:** `python-docx` is optional. If omitted, `.docx` files will be listed but skipped during scrubbing.

## Usage

Run the scrubber from the command line:

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
| `ENTER` | Scrub selected files |
| `c` | Change working directory |
| `h` | Show help |
| `q` | Quit |

## How It Works

### Images

Opens the image, discards all metadata, and re-encodes using only the raw pixel data. This strips EXIF, IPTC, XMP, and any other embedded tags.

### PDFs

Copies all pages to a new PDF and clears the document information dictionary using `pypdf`.

### DOCX

Clears core properties (author, title, dates, etc.) via `python-docx`, then rewrites the ZIP archive with empty `docProps/app.xml` and `docProps/custom.xml` entries to remove extended and custom properties.

## Safety

All writes use an atomic save strategy:

1. Content is written to a temporary file in the same directory.
2. On success, the temporary file is moved to replace the original.
3. On failure, the temporary file is removed and the original is left untouched.

## Requirements

- Python 3.9+
- A modern terminal emulator (Windows Terminal, iTerm2, GNOME Terminal, etc.)
