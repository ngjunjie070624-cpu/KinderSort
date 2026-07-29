"""CustomTkinter GUI entry point for KinderSort.

UI-ONLY REDESIGN NOTE: every method that talks to PhotoSorter (_on_start,
_run_sorting, _on_ref_progress, _on_progress, _on_done, _on_error, the
worker thread, the cancel flag) keeps its original name, signature, and
call sequence. Only widget construction and a handful of *additional*
StringVars (for the new "current image" / "remaining files" / "phase"
display, which the old UI didn't surface) were added. sorter.py,
face_detector.py, and face_recognizer.py are not imported differently and
were not modified for this change.
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
    """Windows 11-styled CustomTkinter shell around the unchanged sorter pipeline."""

    MIN_WIDTH = 860
    MIN_HEIGHT = 760

    # --- Windows 11-inspired palette -----------------------------------
    # (light, dark) tuples, following CustomTkinter's mode-pair convention.
    # ACCENT approximates Windows 11's default system accent blue.
    ACCENT = ("#0067C0", "#60CDFF")
    ACCENT_HOVER = ("#005AA8", "#4CC2FF")
    SUCCESS = ("#0F7B3D", "#3FDB7A")
    SUCCESS_HOVER = ("#0C6631", "#2FBF71")
    DANGER_TEXT = ("#8A1F11", "#FF99A4")
    SURFACE = ("#F3F3F3", "#202020")          # Win11 "Mica"-like app background
    CARD = ("#FFFFFF", "#2B2B2B")             # Win11 card/acrylic surface
    CARD_BORDER = ("#E5E5E5", "#3A3A3A")
    SUBTLE_TEXT = ("#5F5F5F", "#B0B0B0")
    STAT_BG = ("#F5F8FC", "#242A33")

    # Consistent control sizing (requirement 5: rounded buttons, consistent sizing)
    BTN_HEIGHT = 38
    BTN_CORNER = 10
    CARD_CORNER = 14
    BROWSE_BTN_WIDTH = 96
    ACTION_BTN_WIDTH = 150

    def __init__(self) -> None:
        """Configure the themed window and preserve the original application state."""
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("KinderSort AI — Face Recognition & Photo Sorting System")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.geometry("980x820")

        # --- Original application state (unchanged) ---------------------
        self._reference_var = tk.StringVar()
        self._events_var = tk.StringVar()
        self._output_var = tk.StringVar()
        self._cancel_flag = threading.Event()

        self._sort_start_time: float | None = None
        self._ticker_id: str | None = None

        self._count_event_faces = False
        self._event_face_count = 0
        self._face_counter_handler: _FaceCountHandler | None = None

        self._progress_var = tk.DoubleVar(value=0.0)
        self._status_var = tk.StringVar(value="Ready to sort classroom photos.")
        self._progress_text_var = tk.StringVar(value="0%")
        self._stat_vars = {
            "Faces Detected": tk.StringVar(value="0"),
            "Matched": tk.StringVar(value="0"),
            "Unmatched": tk.StringVar(value="0"),
            "Processing Time": tk.StringVar(value="00:00"),
        }

        # --- New display-only state (requirement 6/7: richer status panel
        # and progress bar). These do not feed back into sorting logic —
        # they're populated from the same callbacks the old UI already used.
        self._appearance_var = tk.StringVar(value="Dark")
        self._phase_var = tk.StringVar(value="Idle")
        self._current_image_var = tk.StringVar(value="—")
        self._remaining_var = tk.StringVar(value="—")

        self._build_ui()

    # ------------------------------------------------------------------
    # Windows 11-style layout (presentation only; no sorting logic here)
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the responsive Win11-styled layout: title, 3 folder sections,
        actions, progress card, status panel, and run summary."""
        self.configure(fg_color=self.SURFACE)

        # A scrollable outer frame keeps the window usable if the user
        # shrinks it below the natural content height (requirement 11).
        outer = ctk.CTkScrollableFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=0, pady=0)
        outer.grid_columnconfigure(0, weight=1)

        root = ctk.CTkFrame(outer, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=32, pady=28)
        root.grid_columnconfigure(0, weight=1)

        self._build_header(root)
        self._build_folder_sections(root)
        self._build_action_row(root)
        self._build_progress_card(root)
        self._build_status_panel(root)
        self._build_summary_card(root)

    # -- Title -----------------------------------------------------------

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        """Project title block (requirement 9) plus a Win11-style Light/Dark
        segmented toggle (requirement 10)."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        header.grid_columnconfigure(0, weight=1)

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_block,
            text="KinderSort AI",
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_block,
            text="Face Recognition & Photo Sorting System",
            text_color=self.SUBTLE_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=14),
        ).pack(anchor="w", pady=(2, 0))

        toggle_block = ctk.CTkFrame(header, fg_color="transparent")
        toggle_block.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(
            toggle_block, text="Appearance", text_color=self.SUBTLE_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).pack(anchor="e", pady=(0, 4))
        ctk.CTkSegmentedButton(
            toggle_block,
            values=["Light", "Dark"],
            variable=self._appearance_var,
            command=self._change_appearance,
            corner_radius=self.BTN_CORNER,
            selected_color=self.ACCENT,
            selected_hover_color=self.ACCENT_HOVER,
            width=160,
        ).pack(anchor="e")

    # -- Folder sections (requirement 4) ---------------------------------

    def _build_folder_sections(self, parent: ctk.CTkFrame) -> None:
        """Three distinct grouped cards, one per folder, instead of one
        combined list — makes the three-step setup visually explicit."""
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        wrap.grid_columnconfigure(0, weight=1)

        self._build_folder_section(
            wrap, row=0,
            icon="📁", title="Reference Folder",
            description="One clear photo per student, named by student name.",
            string_var=self._reference_var,
        )
        self._build_folder_section(
            wrap, row=1,
            icon="🏫", title="Classroom Folder",
            description="Event photo subfolders to be sorted (e.g. Sports_Day, Concert).",
            string_var=self._events_var,
        )
        self._build_folder_section(
            wrap, row=2,
            icon="📤", title="Output Folder",
            description="Where sorted student folders and the log file will be written.",
            string_var=self._output_var,
        )

    def _build_folder_section(
        self,
        parent: ctk.CTkFrame,
        row: int,
        icon: str,
        title: str,
        description: str,
        string_var: tk.StringVar,
    ) -> None:
        """One self-contained Win11-style card: icon + title + description
        on top, path entry + rounded Browse button below."""
        card = ctk.CTkFrame(
            parent, fg_color=self.CARD, corner_radius=self.CARD_CORNER,
            border_width=1, border_color=self.CARD_BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkFrame(card, fg_color="transparent")
        heading.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            heading, text=f"{icon}  {title}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            heading, text=description, text_color=self.SUBTLE_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).pack(anchor="w", pady=(1, 0))

        row_frame = ctk.CTkFrame(card, fg_color="transparent")
        row_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 16))
        row_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            row_frame,
            textvariable=string_var,
            placeholder_text="Choose a folder…",
            height=self.BTN_HEIGHT,
            corner_radius=self.BTN_CORNER,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(
            row_frame,
            text="Browse",
            width=self.BROWSE_BTN_WIDTH,
            height=self.BTN_HEIGHT,
            corner_radius=self.BTN_CORNER,
            command=lambda value=string_var: self._browse_folder(value),
        ).grid(row=0, column=1)

    # -- Actions (requirement 5: consistent rounded buttons) -------------

    def _build_action_row(self, parent: ctk.CTkFrame) -> None:
        """Start/Cancel actions, same handlers as before, restyled for
        consistent sizing and Win11 accent colors."""
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(4, 18))

        self._start_btn = ctk.CTkButton(
            actions,
            text="▶  Start Sorting",
            width=self.ACTION_BTN_WIDTH,
            height=self.BTN_HEIGHT + 6,
            corner_radius=self.BTN_CORNER,
            fg_color=self.SUCCESS,
            hover_color=self.SUCCESS_HOVER,
            font=ctk.CTkFont(family="Segoe UI", weight="bold"),
            command=self._on_start,
        )
        self._start_btn.pack(side="left")

        self._cancel_btn = ctk.CTkButton(
            actions,
            text="Cancel",
            width=110,
            height=self.BTN_HEIGHT + 6,
            corner_radius=self.BTN_CORNER,
            fg_color=("#D9DEE8", "#3A4252"),
            text_color=("#252B35", "#F4F6FA"),
            hover_color=("#C8CFDC", "#4B5568"),
            state="disabled",
            command=self._on_cancel,
        )
        self._cancel_btn.pack(side="left", padx=(10, 0))

    # -- Progress card (requirement 7) ------------------------------------

    def _build_progress_card(self, parent: ctk.CTkFrame) -> None:
        """Progress bar with percentage, current file name, and remaining
        file count all visible at once."""
        card = ctk.CTkFrame(
            parent, fg_color=self.CARD, corner_radius=self.CARD_CORNER,
            border_width=1, border_color=self.CARD_BORDER,
        )
        card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top, text="Progress", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            top, textvariable=self._progress_text_var,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.ACCENT,
        ).grid(row=0, column=1, sticky="e")

        self._progress_bar = ctk.CTkProgressBar(
            card, variable=self._progress_var, height=10, corner_radius=8,
            progress_color=self.ACCENT,
        )
        self._progress_bar.grid(row=1, column=0, sticky="ew", padx=18)
        self._progress_bar.set(0)

        detail = ctk.CTkFrame(card, fg_color="transparent")
        detail.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 4))
        detail.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            detail, textvariable=self._current_image_var,
            anchor="w", font=ctk.CTkFont(family="Segoe UI", size=12),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            detail, textvariable=self._remaining_var,
            anchor="e", text_color=self.SUBTLE_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            card, textvariable=self._status_var,
            anchor="w", justify="left",
            text_color=self.SUBTLE_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(2, 16))

    # -- Status panel (requirement 6) ------------------------------------

    def _build_status_panel(self, parent: ctk.CTkFrame) -> None:
        """Dedicated status panel: current processing phase as a headline
        pill, plus the four running-total stat cards."""
        card = ctk.CTkFrame(
            parent, fg_color=self.CARD, corner_radius=self.CARD_CORNER,
            border_width=1, border_color=self.CARD_BORDER,
        )
        card.grid(row=4, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        head.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            head, text="Status", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            head, textvariable=self._phase_var,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.ACCENT, anchor="e",
        ).grid(row=0, column=1, sticky="e")

        stats = ctk.CTkFrame(card, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 16))
        for column, title in enumerate(self._stat_vars):
            stats.grid_columnconfigure(column, weight=1, uniform="status")
            self._build_stat_card(stats, title, column)

    def _build_stat_card(self, parent: ctk.CTkFrame, title: str, column: int) -> None:
        """One compact stat card; values update from the existing callbacks/logs."""
        card = ctk.CTkFrame(parent, fg_color=self.STAT_BG, corner_radius=12)
        card.grid(row=0, column=column, sticky="ew", padx=6)
        ctk.CTkLabel(
            card, text=title, text_color=self.SUBTLE_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        ).pack(anchor="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(
            card, textvariable=self._stat_vars[title],
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(0, 10))

    # -- Run summary -------------------------------------------------------

    def _build_summary_card(self, parent: ctk.CTkFrame) -> None:
        """Read-only completion summary in a styled container (unchanged content)."""
        card = ctk.CTkFrame(
            parent, fg_color=self.CARD, corner_radius=self.CARD_CORNER,
            border_width=1, border_color=self.CARD_BORDER,
        )
        card.grid(row=5, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card, text="Run Summary", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))
        self._summary_text = ctk.CTkTextbox(
            card,
            height=140,
            corner_radius=10,
            border_width=0,
            fg_color=self.STAT_BG,
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self._summary_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._summary_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Existing event flow — unchanged control logic; only extra display
    # variables are set alongside the original ones.
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
        for path, name in [(ref_path, "Reference"), (events_path, "Classroom")]:
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
        self._current_image_var.set("—")
        self._remaining_var.set("—")
        self._phase_var.set("Loading references")
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

        self._count_event_faces = True
        self.after(0, self._phase_var.set, "Sorting photos")
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
        self.after(0, self._current_image_var.set, f"Reference: {name}")

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
        self._phase_var.set("Cancelling")
        self._set_status("Cancelling… (finishing current image)")

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        """Schedule progress updates from the existing worker-thread callback."""
        self.after(0, self._apply_progress, current, total, filename)

    def _apply_progress(self, current: int, total: int, filename: str) -> None:
        """Update GUI state for the current event image, including the new
        current-image and remaining-file displays."""
        fraction = (current / total) if total else 0.0
        self._progress_var.set(fraction)
        self._progress_bar.set(fraction)
        self._progress_text_var.set(f"{fraction * 100:.0f}%")
        self._current_image_var.set(f"Current: {filename}")
        remaining = max(total - current, 0)
        self._remaining_var.set(f"{remaining} remaining")
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
        self._remaining_var.set("0 remaining")
        self._set_stat("Matched", str(summary["matched"]))
        self._set_stat("Unmatched", str(summary["unmatched"]))

        cancelled = self._cancel_flag.is_set()
        status = "Sorting cancelled." if cancelled else "Sorting complete."
        self._phase_var.set("Cancelled" if cancelled else "Complete")
        self._current_image_var.set(status)
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
                "No photos were found in the Classroom folder.\n\nSupported formats: .jpg  .jpeg  .png  .bmp  .webp",
            )

    def _on_error(self, message: str) -> None:
        """Restore controls after an existing worker error and show its message."""
        self._count_event_faces = False
        self._stop_ticker()
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._phase_var.set("Error")
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