#!/usr/bin/env python3
import argparse
import asyncio
import os
import locale
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal
    from textual.widgets import Header, Footer, DataTable, Static, Input, Button, ProgressBar
    from textual.reactive import reactive
    from textual.screen import ModalScreen
except ImportError as e:
    raise ImportError(
        "textual is required for the terminal UI. "
        "Install with: pip install textual"
    ) from e

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from PIL import Image, ImageSequence
except ImportError:
    Image = None
    ImageSequence = None

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".gif"}
PDF_EXT = {".pdf"}
DOCX_EXT = {".docx"}
SUPPORTED_EXT = IMAGE_EXT | PDF_EXT | DOCX_EXT
EXT_TYPE = {ext: "Image" for ext in IMAGE_EXT}
EXT_TYPE.update({".pdf": "PDF", ".docx": "Word"})
EXT_REQUIREMENTS = {
    **{ext: "pillow" for ext in IMAGE_EXT},
    ".pdf": "pypdf",
    ".docx": "python-docx",
}

SCRUBBERS: Dict[str, Callable[[str], None]] = {}


def missing_packages() -> List[str]:
    return sorted({pkg for ext, pkg in EXT_REQUIREMENTS.items() if ext not in SCRUBBERS})


def file_type_label(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    label = EXT_TYPE.get(ext, ext.lstrip("."))
    if ext not in SCRUBBERS:
        requirement = EXT_REQUIREMENTS.get(ext, "required package")
        return f"{label} (missing {requirement})"
    return label


def file_status_label(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in SCRUBBERS:
        return "Ready"
    requirement = EXT_REQUIREMENTS.get(ext, "package")
    return f"Missing {requirement}"


def atomic_save(filepath: str, write_func: Callable[[str], None], suffix: Optional[str] = None) -> None:
    original_mode = os.stat(filepath).st_mode
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, dir=Path(filepath).parent)
    try:
        os.close(fd)
        write_func(tmp_path)
        os.chmod(tmp_path, original_mode)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def scrub_image(filepath: str) -> None:
    with Image.open(filepath) as img:
        fmt = img.format
        is_animated = fmt == "GIF" and getattr(img, "n_frames", 1) > 1

        if is_animated:
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(img):
                clean = Image.new(frame.mode, frame.size)
                clean.putdata(list(frame.getdata()))
                frames.append(clean)
                durations.append(frame.info.get("duration", 0))
            loop = img.info.get("loop", 0)

            def write(p: str) -> None:
                frames[0].save(
                    p,
                    format=fmt,
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=loop,
                    disposal=2,
                )
        else:
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))

            def write(p: str) -> None:
                clean_img.save(p, format=fmt)

    atomic_save(filepath, write, suffix=Path(filepath).suffix)


def scrub_pdf(filepath: str) -> None:
    if PdfWriter is None:
        raise ImportError("pypdf is required for PDF scrubbing. Install with: pip install pypdf")

    def write(p: str) -> None:
        reader = PdfReader(filepath)
        pdf_writer = PdfWriter()
        for page in reader.pages:
            pdf_writer.add_page(page)
        pdf_writer.add_metadata({})
        with open(p, "wb") as f:
            pdf_writer.write(f)

    atomic_save(filepath, write, suffix=".pdf")


def scrub_docx(filepath: str) -> None:
    if Document is None:
        raise ImportError("python-docx is required for DOCX scrubbing. Install with: pip install python-docx")
    doc = Document(filepath)
    cp = doc.core_properties
    cp.author = ""
    cp.category = ""
    cp.comments = ""
    cp.content_status = ""
    cp.created = None
    cp.identifier = ""
    cp.keywords = ""
    cp.language = ""
    cp.last_modified_by = ""
    cp.last_printed = None
    cp.modified = None
    cp.revision = ""
    cp.subject = ""
    cp.title = ""
    cp.version = ""

    def write(p: str) -> None:
        doc.save(p)
        with zipfile.ZipFile(p, "r") as zin:
            items = [(name, zin.read(name)) for name in zin.namelist()]
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, content in items:
                if name == "docProps/app.xml":
                    zout.writestr(
                        name,
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\"></Properties>",
                    )
                elif name == "docProps/custom.xml":
                    zout.writestr(
                        name,
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                        "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/custom-properties\"></Properties>",
                    )
                else:
                    zout.writestr(name, content)

    atomic_save(filepath, write, suffix=".docx")


if Image is not None:
    for ext in IMAGE_EXT:
        SCRUBBERS[ext] = scrub_image
if PdfWriter is not None:
    for ext in PDF_EXT:
        SCRUBBERS[ext] = scrub_pdf
if Document is not None:
    for ext in DOCX_EXT:
        SCRUBBERS[ext] = scrub_docx


def get_files(directory: str) -> List[str]:
    files: List[str] = []
    try:
        with os.scandir(directory) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                ext = Path(entry.name).suffix.lower()
                if ext not in SUPPORTED_EXT:
                    continue
                files.append(entry.path)
    except OSError as exc:
        raise RuntimeError(f"cannot access directory: {directory}") from exc
    return sorted(files)


class DirectoryModal(ModalScreen):
    BINDINGS = [
        ("enter", "submit", "Submit"),
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Container():
            yield Input(placeholder="Enter directory path", id="dir-input")
            with Horizontal():
                yield Button("OK", id="ok", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one("#dir-input").value)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_submit(self) -> None:
        self.dismiss(self.query_one("#dir-input").value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmModal(ModalScreen):
    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, count: int) -> None:
        super().__init__()
        self.count = count

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"Scrub {self.count} file(s)? This cannot be undone.", id="confirm-text", markup=False)
            with Horizontal():
                yield Button("Yes", id="yes", variant="primary")
                yield Button("No", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ProgressModal(ModalScreen):
    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Scrubbing...", id="progress-title")
            yield ProgressBar(id="progress-bar")
            yield Static("", id="progress-text", markup=False)

    def update_progress(self, current: int, total: int, filename: str) -> None:
        self.query_one("#progress-bar").total = total
        self.query_one("#progress-bar").progress = current / total
        self.query_one("#progress-text").update(f"{current}/{total} {filename}")


class MetadataScrubberApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    DataTable {
        height: 1fr;
    }
    #status {
        height: 3;
        content-align: center middle;
        background: $panel;
        text-style: bold;
    }
    DirectoryModal, ConfirmModal, ProgressModal {
        align: center middle;
    }
    DirectoryModal > Container,
    ConfirmModal > Container,
    ProgressModal > Container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }
    """

    BINDINGS = [
        ("space", "toggle_select", "Toggle"),
        ("a", "select_all", "All"),
        ("d", "deselect_all", "None"),
        ("enter", "scrub", "Scrub"),
        ("s", "scrub_all", "Scrub All"),
        ("r", "reload", "Reload"),
        ("c", "change_dir", "Dir"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
    ]

    current_dir: reactive[str] = reactive("")
    files: reactive[List[str]] = reactive([])
    selected: reactive[Set[int]] = reactive(set())
    message: reactive[str] = reactive("Ready")

    def __init__(self, start_dir: str = "", **kwargs):
        super().__init__(**kwargs)
        self.start_dir = start_dir

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="info", markup=False)
        yield DataTable(id="file-table")
        yield Static("", id="preview", markup=False)
        yield Static("Ready", id="status", markup=False)
        yield Footer()

    def on_mount(self):
        self.current_dir = self.start_dir or os.getcwd()
        self.load_files()
        table = self.query_one("#file-table")
        table.cursor_type = "row"
        table.add_column("", key="sel", width=4)
        table.add_column("File", key="name", width=40)
        table.add_column("Type", key="type", width=16)
        table.add_column("Status", key="status", width=12)

    def watch_message(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def load_files(self):
        self.files = get_files(self.current_dir)
        self.selected.clear()
        self.update_table()
        missing = missing_packages()
        if missing:
            self.message = f"{len(self.files)} files - missing: {', '.join(missing)}"
        else:
            self.message = f"Loaded {len(self.files)} files from {self.current_dir}"

    def update_info(self) -> None:
        info = self.query_one("#info", Static)
        total = len(self.files)
        selected = len(self.selected)
        info.update(f"Directory: {self.current_dir} | Files: {total} | Selected: {selected}")

    def update_table(self):
        table = self.query_one("#file-table")
        table.clear(columns=False)
        for i, f in enumerate(self.files):
            table.add_row(
                "[X]" if i in self.selected else "[ ]",
                os.path.basename(f),
                file_type_label(f),
                file_status_label(f),
                key=str(i),
            )
        if self.files:
            table.move_cursor(row=0)
        self.update_info()

    def update_selection_display(self):
        if not self.files:
            return
        table = self.query_one("#file-table")
        for i in range(len(self.files)):
            table.update_cell(
                row_key=str(i),
                column_key="sel",
                value="[X]" if i in self.selected else "[ ]",
            )
        self.update_info()

    def action_toggle_select(self):
        table = self.query_one("#file-table")
        row = table.cursor_row
        if 0 <= row < len(self.files):
            if row in self.selected:
                self.selected.remove(row)
            else:
                self.selected.add(row)
            self.update_selection_display()

    def action_select_all(self):
        self.selected = set(range(len(self.files)))
        self.update_selection_display()
        self.message = "All files selected"

    def action_deselect_all(self):
        self.selected.clear()
        self.update_selection_display()
        self.message = "Selection cleared"

    def action_scrub(self):
        if not self.selected:
            self.message = "No files selected"
            return
        self.push_screen(ConfirmModal(len(self.selected)), self.on_scrub_confirmed)

    def action_reload(self):
        self.load_files()
        self.message = "Directory reloaded"

    def action_scrub_all(self):
        if not self.files:
            self.message = "No files to scrub"
            return
        self.selected = set(range(len(self.files)))
        self.update_selection_display()
        self.push_screen(ConfirmModal(len(self.files)), self.on_scrub_confirmed)

    def action_change_dir(self):
        self.push_screen(DirectoryModal(), self.on_directory_selected)

    def action_help(self):
        self.message = "SPACE toggle selection, ENTER scrub selected, S scrub all, A select all, D clear"

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key
        if hasattr(row_key, 'value'):
            row_key = row_key.value
        self.update_preview(int(row_key))

    def update_preview(self, row_index: int) -> None:
        preview = self.query_one("#preview", Static)
        if row_index < 0 or row_index >= len(self.files):
            preview.update("No file selected")
            return
        filepath = self.files[row_index]
        ext = Path(filepath).suffix.lower()
        if ext in IMAGE_EXT and Image is not None:
            preview.update(self.render_image_preview(filepath))
            return
        preview.update(
            f"{os.path.basename(filepath)}\n{file_type_label(filepath)}\n{file_status_label(filepath)}"
        )

    def render_image_preview(self, filepath: str) -> str:
        try:
            with Image.open(filepath) as img:
                img = img.convert("L")
                width = min(32, img.width)
                height = min(12, max(1, int(width * img.height / img.width / 2)))
                img = img.resize((width, height))
                shades = "@%#*+=-:. "
                lines = []
                for y in range(height):
                    row = ""
                    for x in range(width):
                        pixel = img.getpixel((x, y))
                        row += shades[pixel * (len(shades) - 1) // 255]
                    lines.append(row)
                return "\n".join(lines)
        except Exception as e:
            return f"Could not render preview: {e}"

    def on_directory_selected(self, new_dir: Optional[str]):
        if new_dir:
            new_dir = os.path.expanduser(new_dir.strip())
            if os.path.isdir(new_dir):
                self.current_dir = new_dir
                self.load_files()
                self.message = f"Changed to {new_dir}"
            else:
                self.message = f"Not a directory: {new_dir}"
        else:
            self.message = "Directory change cancelled"

    def on_scrub_confirmed(self, confirmed: Optional[bool]) -> None:
        if confirmed:
            self.scrub_selected()
        else:
            self.message = "Scrub cancelled"

    def scrub_selected(self):
        to_process = [self.files[i] for i in sorted(self.selected)]
        total = len(to_process)
        progress_modal = ProgressModal()

        async def do_scrub():
            self.push_screen(progress_modal)
            success = 0
            fail = 0
            for idx, filepath in enumerate(to_process, start=1):
                progress_modal.update_progress(idx, total, os.path.basename(filepath))
                try:
                    ext = Path(filepath).suffix.lower()
                    scrubber = SCRUBBERS.get(ext)
                    if scrubber is None:
                        raise ValueError(f"no scrubber available for {ext}")
                    await asyncio.to_thread(scrubber, filepath)
                    success += 1
                except Exception as e:
                    fail += 1
                    self.message = f"Failed: {os.path.basename(filepath)} ({e})"
                    await asyncio.sleep(0)
            self.pop_screen()
            self.message = f"Done: {success} succeeded, {fail} failed"
            self.selected.clear()
            self.load_files()

        self.run_worker(do_scrub())


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrub metadata from images, PDFs, and DOCX files.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to scan for supported files",
    )
    args = parser.parse_args()
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass
    MetadataScrubberApp(start_dir=os.path.abspath(args.directory)).run()


if __name__ == "__main__":
    main()
