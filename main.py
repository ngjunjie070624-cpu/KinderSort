"""CustomTkinter GUI entry point for KinderSort.

The interface is intentionally separate from the PhotoSorter pipeline: it
keeps the existing worker-thread, callbacks, and sorting behaviour unchanged.
"""

import logging
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from sorter import PhotoSorter
from utils import setup_logger


class _FaceCountHandler(logging.Handler):
    """UI-only log listener that totals detected event faces without changing sorting."""

    _DETECTION_PATTERN = re.compile(r"^(?:SCRFD|YOLO) detected (\d+) face\(s\)$")

    def __init__(self, app: "KinderSortApp") -> None:
        super().__init__(level=logging.INFO)
        self._app = app

    def emit(self, record: logging.LogRecord) -> None:
        """Read detector logs emitted during event sorting and refresh the status card."""
        match = self._DETECTION_PATTERN.match(record.getMessage())
        if match is None or not self._app._count_event_faces:
            return
        self._app._event_face_count += int(match.group(1))
        self._app.after(0, self._app._set_stat, "Faces Detected", str(self._app._event_face_count))


class KinderSortApp(ctk.CTk):
    """Modern, low-overhead CustomTkinter shell around the existing sorter."""

    MIN_WIDTH = 780
    MIN_HEIGHT = 650
    ACCENT = "#4F8EF7"
    SUCCESS = "#2FBF71"
    SURFACE = ("#F6F8FB", "#1B1F2A")
    CARD = ("#FFFFFF", "#252B38")

    def __init__(self) -> None:
        """Configure the themed window and preserve the original application state."""
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("KinderSort v1.1 — Student Photo Organiser")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.geometry("900x720")

        # These variables and the cancellation event are unchanged application state.
        self._reference_var = tk.StringVar()
        self._events_var = tk.StringVar()
        self._output_var = tk.StringVar()
        self._cancel_flag = threading.Event()

        # Lightweight timer state; UI refreshes every 250 ms while sorting only.
        self._sort_start_time: float | None = None
        self._ticker_id: str | None = None

        # GUI telemetry derives the face total from existing detector logs.
        self._count_event_faces = False
        self._event_face_count = 0
        self._face_counter_handler: _FaceCountHandler | None = None

        self._appearance_var = tk.StringVar(value="Dark")
        self._progress_var = tk.DoubleVar(value=0.0)
        self._status_var = tk.StringVar(value="Ready to sort classroom photos.")
        self._progress_text_var = tk.StringVar(value="0%")
        self._stat_vars = {
            "Faces Detected": tk.StringVar(value="0"),
            "Matched": tk.StringVar(value="0"),
            "Unmatched": tk.StringVar(value="0"),
            "Processing Time": tk.StringVar(value="00:00"),
        }

        self._build_ui()

    # ------------------------------------------------------------------
    # Modern CustomTkinter layout (presentation only; no sorting logic here)
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the responsive dark-mode layout with rounded controls and cards."""
        self.configure(fg_color=self.SURFACE)
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=28, pady=24)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(4, weight=1)

        self._build_header(root)
        self._build_folder_card(root)
        self._build_action_row(root)
        self._build_progress_card(root)
        self._build_summary_card(root)

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        """Create the title area and user-selectable light/dark/system mode."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="KinderSort",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Student photo organiser",
            text_color=("#5D6472", "#A9B0BE"),
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkOptionMenu(
            header,
            values=["Dark", "Light", "System"],
            variable=self._appearance_var,
            command=self._change_appearance,
            width=112,
            corner_radius=10,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_folder_card(self, parent: ctk.CTkFrame) -> None:
        """Build the rounded folder-selection card using the original path variables."""
        card = ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=16)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card, text="Folders", font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(16, 10))

        self._build_folder_row(card, "Reference photos", self._reference_var, 1)
        self._build_folder_row(card, "Events folder", self._events_var, 2)
        self._build_folder_row(card, "Output folder", self._output_var, 3)

    def _build_folder_row(
        self,
        parent: ctk.CTkFrame,
        label_text: str,
        string_var: tk.StringVar,
        row: int,
    ) -> None:
        """Create one spacious label, path entry, and rounded browse button row."""
        ctk.CTkLabel(parent, text=label_text, width=120, anchor="w").grid(
            row=row, column=0, sticky="w", padx=(18, 10), pady=7
        )
        ctk.CTkEntry(
            parent,
            textvariable=string_var,
            placeholder_text="Choose a folder…",
            height=36,
            corner_radius=9,
        ).grid(row=row, column=1, sticky="ew", pady=7)
        ctk.CTkButton(
            parent,
            text="Browse",
            width=82,
            height=36,
            corner_radius=9,
            command=lambda value=string_var: self._browse_folder(value),
        ).grid(row=row, column=2, padx=(10, 18), pady=7)

    def _build_action_row(self, parent: ctk.CTkFrame) -> None:
        """Build rounded start/cancel actions without changing their handlers."""
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        actions.grid_columnconfigure(2, weight=1)

        self._start_btn = ctk.CTkButton(
            actions,
            text="Start sorting",
            height=42,
            corner_radius=12,
            fg_color=self.SUCCESS,
            hover_color="#24985A",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_start,
        )
        self._start_btn.grid(row=0, column=0, sticky="w")
        self._cancel_btn = ctk.CTkButton(
            actions,
            text="Cancel",
            height=42,
            width=100,
            corner_radius=12,
            fg_color=("#D9DEE8", "#3A4252"),
            text_color=("#252B35", "#F4F6FA"),
            hover_color=("#C8CFDC", "#4B5568"),
            state="disabled",
            command=self._on_cancel,
        )
        self._cancel_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))

    def _build_progress_card(self, parent: ctk.CTkFrame) -> None:
        """Build progress, current status, and requested sorting-status panel."""
        card = ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=16)
        card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="Progress", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(top, textvariable=self._progress_text_var).grid(row=0, column=1, sticky="e")

        self._progress_bar = ctk.CTkProgressBar(card, variable=self._progress_var, height=12, corner_radius=8)
        self._progress_bar.grid(row=1, column=0, sticky="ew", padx=18)
        self._progress_bar.set(0)
        ctk.CTkLabel(
            card,
            textvariable=self._status_var,
            anchor="w",
            justify="left",
            text_color=("#5D6472", "#A9B0BE"),
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 14))

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 14))
        for column, title in enumerate(self._stat_vars):
            stats.grid_columnconfigure(column, weight=1, uniform="status")
            self._build_stat_card(stats, title, column)

    def _build_stat_card(self, parent: ctk.CTkFrame, title: str, column: int) -> None:
        """Create one compact status card; values update from existing callbacks/logs."""
        card = ctk.CTkFrame(parent, fg_color=("#EDF2FA", "#1E2430"), corner_radius=12)
        card.grid(row=0, column=column, sticky="ew", padx=6)
        ctk.CTkLabel(
            card, text=title, text_color=("#687184", "#9DA6B8"), font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=12, pady=(9, 0))
        ctk.CTkLabel(
            card, textvariable=self._stat_vars[title], font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=12, pady=(0, 9))

    def _build_summary_card(self, parent: ctk.CTkFrame) -> None:
        """Build the existing read-only completion summary in a styled container."""
        card = ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=16)
        card.grid(row=4, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(card, text="Run summary", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )
        self._summary_text = ctk.CTkTextbox(
            card,
            height=130,
            corner_radius=10,
            border_width=0,
            fg_color=("#EEF2F8", "#171B24"),
            font=ctk.CTkFont(size=13),
        )
        self._summary_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._summary_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Existing event flow; only widget calls are CustomTkinter equivalents
    # ------------------------------------------------------------------

    def _change_appearance(self, value: str) -> None:
        """Switch CustomTkinter appearance mode without affecting processing."""
        ctk.set_appearance_mode(value.lower())

    def _browse_folder(self, string_var: tk.StringVar) -> None:
        """Open the original directory chooser and store the selected path."""
        folder = filedialog.askdirectory(title="Select folder")
        if folder:
            string_var.set(folder)

    def _on_start(self) -> None:
        """Validate folders and launch the unchanged background sorting worker."""
        ref = self._reference_var.get().strip()
        events = self._events_var.get().strip()
        output = self._output_var.get().strip()
        if not ref or not events or not output:
            messagebox.showerror("Missing folders", "Please select all three folders before starting.")
            return

        ref_path, events_path, output_path = Path(ref), Path(events), Path(output)
        for path, name in [(ref_path, "Reference"), (events_path, "Events")]:
            if not path.is_dir():
                messagebox.showerror("Invalid folder", f"{name} folder does not exist:\n{path}")
                return
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Output folder error", f"Cannot create output folder:\n{exc}")
            return

        self._start_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._cancel_flag.clear()
        self._count_event_faces = False
        self._event_face_count = 0
        self._progress_var.set(0.0)
        self._progress_bar.set(0.0)
        self._progress_text_var.set("0%")
        for title, value in (("Faces Detected", "0"), ("Matched", "0"), ("Unmatched", "0"), ("Processing Time", "00:00")):
            self._set_stat(title, value)
        self._clear_summary()
        self._set_status("Loading reference photos…")
        self._start_ticker()

        logger = setup_logger(output_path)
        self._face_counter_handler = _FaceCountHandler(self)
        logger.addHandler(self._face_counter_handler)
        sorter = PhotoSorter(ref_path, events_path, output_path, logger)
        threading.Thread(target=self._run_sorting, args=(sorter,), daemon=True).start()

    def _run_sorting(self, sorter: PhotoSorter) -> None:
        """Original worker sequence: load references, then process event images."""
        try:
            skipped_names = sorter.load_references(progress_callback=self._on_ref_progress)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, str(exc))
            return
        if skipped_names:
            self.after(0, self._show_ref_warning, skipped_names)
        if not sorter._student_encodings:
            self.after(0, self._on_error, "No student faces could be loaded. Please check your Reference folder.")
            return

        # This flag only scopes GUI log telemetry to event photos, not references.
        self._count_event_faces = True
        try:
            summary = sorter.sort_all(progress_callback=self._on_progress, cancelled=self._cancel_flag.is_set)
            self._count_event_faces = False
            self.after(0, self._on_done, summary)
        except Exception as exc:  # noqa: BLE001
            self._count_event_faces = False
            self.after(0, self._on_error, str(exc))

    def _start_ticker(self) -> None:
        """Start the existing low-frequency elapsed-time display."""
        self._sort_start_time = time.monotonic()
        self._tick()

    def _tick(self) -> None:
        """Refresh elapsed time at 250 ms; no image or model work occurs here."""
        if self._sort_start_time is None:
            return
        elapsed = int(time.monotonic() - self._sort_start_time)
        minutes, seconds = divmod(elapsed, 60)
        self._set_stat("Processing Time", f"{minutes:02d}:{seconds:02d}")
        self._ticker_id = self.after(250, self._tick)

    def _stop_ticker(self, final_elapsed: int | None = None) -> None:
        """Stop timer updates and retain the completed duration in the status panel."""
        if self._ticker_id:
            self.after_cancel(self._ticker_id)
            self._ticker_id = None
        if final_elapsed is not None:
            minutes, seconds = divmod(final_elapsed, 60)
            self._set_stat("Processing Time", f"{minutes:02d}:{seconds:02d}")
        self._sort_start_time = None

    def _on_ref_progress(self, current: int, total: int, name: str) -> None:
        """Forward existing reference-load progress to the main GUI thread."""
        self.after(0, self._set_status, f"Loading references [{current}/{total}]: {name}…")

    def _show_ref_warning(self, skipped_names: list[str]) -> None:
        """Preserve the original warning when reference images contain no usable face."""
        names_str = "\n".join(f"  • {name}" for name in skipped_names)
        messagebox.showwarning(
            "Reference photos without faces",
            f"No face was detected in the reference photos for:\n\n{names_str}\n\nThese students will be skipped during sorting.",
        )

    def _on_cancel(self) -> None:
        """Preserve cancellation behaviour; the worker stops after its current image."""
        self._cancel_flag.set()
        self._cancel_btn.configure(state="disabled")
        self._set_status("Cancelling… (finishing current image)")

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        """Schedule progress updates from the existing worker-thread callback."""
        self.after(0, self._apply_progress, current, total, filename)

    def _apply_progress(self, current: int, total: int, filename: str) -> None:
        """Update only lightweight GUI state for the current event image."""
        fraction = (current / total) if total else 0.0
        self._progress_var.set(fraction)
        self._progress_bar.set(fraction)
        self._progress_text_var.set(f"{fraction * 100:.0f}%")
        self._set_status(f"[{current}/{total}] {filename}")

    def _on_done(self, summary: dict[str, int]) -> None:
        """Show original completion totals in both status cards and summary text."""
        elapsed = int(time.monotonic() - self._sort_start_time) if self._sort_start_time else None
        self._stop_ticker(final_elapsed=elapsed)
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._progress_var.set(1.0)
        self._progress_bar.set(1.0)
        self._progress_text_var.set("100%")
        self._set_stat("Matched", str(summary["matched"]))
        self._set_stat("Unmatched", str(summary["unmatched"]))

        cancelled = self._cancel_flag.is_set()
        status = "Sorting cancelled." if cancelled else "Sorting complete."
        self._set_status(status)
        self._write_summary("\n".join([
            status,
            "",
            f"Total images found : {summary['total']}",
            f"Faces detected     : {self._event_face_count}",
            f"Matched (sorted)   : {summary['matched']}",
            f"Unmatched          : {summary['unmatched']}",
            f"Skipped (errors)   : {summary['skipped']}",
        ]))
        if summary["total"] == 0:
            messagebox.showwarning(
                "No images found",
                "No photos were found in the Events folder.\n\nSupported formats: .jpg  .jpeg  .png  .bmp  .webp",
            )

    def _on_error(self, message: str) -> None:
        """Restore controls after an existing worker error and show its message."""
        self._count_event_faces = False
        self._stop_ticker()
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._set_status("An error occurred.")
        messagebox.showerror("Unexpected error", message)

    # ------------------------------------------------------------------
    # CustomTkinter widget helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        """Update the current status message without performing any processing."""
        self._status_var.set(text)

    def _set_stat(self, title: str, value: str) -> None:
        """Set a status-card value by title."""
        self._stat_vars[title].set(value)

    def _write_summary(self, text: str) -> None:
        """Write completion text into the styled, read-only CustomTkinter box."""
        self._summary_text.configure(state="normal")
        self._summary_text.delete("0.0", "end")
        self._summary_text.insert("0.0", text)
        self._summary_text.configure(state="disabled")

    def _clear_summary(self) -> None:
        """Clear the existing summary area before a new run."""
        self._write_summary("")


def main() -> None:
    """Launch the CustomTkinter KinderSort application."""
    KinderSortApp().mainloop()


if __name__ == "__main__":
    main()
