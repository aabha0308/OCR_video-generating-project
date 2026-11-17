
import csv
import shutil
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from PIL import Image, ImageDraw, ImageTk


# ============================================================
# PATHS AND SETTINGS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

SOURCE_DIR = ROOT / "data" / "annotations" / "ocr_validation"

WORKBENCH_DIR = (
    ROOT / "data" / "annotations" / "ocr_validation"
    / "workbench_v1"
)

AUDIT_FILE = (
    ROOT / "reports" / "day16_gt_ocr_line_mapping_audit.csv"
)

RAW_IMAGE_DIR = (
    ROOT / "data" / "raw" / "invoices" / "archive"
    / "ImageAndXML_Data"
)

DOCUMENTS = [
    "507484246",
    "2061828225",
    "ti31149327_9330",
    "503116473+-6473",
    "96052028",
]

STATUSES = [
    "pending",
    "correct",
    "minor_error",
    "major_error",
    "non_text",
    "unreadable",
]

TRAINING_STATUSES = {
    "correct",
    "minor_error",
    "major_error",
}


# ============================================================
# FILE HELPERS
# ============================================================

def read_csv(path):
    with path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        return list(csv.DictReader(f))


def write_csv_atomic(path, rows):
    if not rows:
        raise ValueError(f"No rows to save: {path}")

    columns = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            delete=False,
            dir=path.parent,
            suffix=".tmp",
        ) as f:
            temp_path = Path(f.name)
            writer = csv.DictWriter(
                f, fieldnames=columns
            )
            writer.writeheader()
            writer.writerows(rows)

        temp_path.replace(path)

    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise


def find_tiff(document_id):
    for extension in (".tif", ".tiff", ".TIF", ".TIFF"):
        path = RAW_IMAGE_DIR / f"{document_id}{extension}"
        if path.exists():
            return path
    raise FileNotFoundError(
        f"TIFF not found for document {document_id}"
    )


def load_font_image(image, max_width, max_height):
    image = image.copy()
    image.thumbnail(
        (max_width, max_height),
        Image.Resampling.LANCZOS,
    )
    return ImageTk.PhotoImage(image)


# ============================================================
# ANNOTATION APPLICATION
# ============================================================

class AnnotationApp:

    def __init__(self, root):
        self.root = root
        self.root.title("OCR Human Annotation Review")
        self.root.geometry("1450x950")
        self.root.minsize(1100, 750)

        self.datasets = {}
        self.audit = {}
        self.current_document = None
        self.current_index = None
        self.current_image = None
        self.current_image_path = None

        self.page_photo = None
        self.crop_photo = None
        self.loading = False

        self.prepare_workbench()
        self.load_audit()
        self.load_datasets()
        self.build_interface()

        self.document_var.set(DOCUMENTS[0])
        self.change_document()

        self.root.protocol(
            "WM_DELETE_WINDOW", self.close_application
        )

    # --------------------------------------------------------
    # Prepare separate working copies
    # --------------------------------------------------------

    def prepare_workbench(self):
        WORKBENCH_DIR.mkdir(
            parents=True, exist_ok=True
        )

        for document_id in DOCUMENTS:
            source = (
                SOURCE_DIR
                / f"document_{document_id}_review.csv"
            )

            destination = (
                WORKBENCH_DIR
                / f"document_{document_id}_review.csv"
            )

            if not destination.exists():
                if not source.exists():
                    raise FileNotFoundError(source)

                shutil.copy2(source, destination)

    def load_audit(self):
        rows = read_csv(AUDIT_FILE)

        for row in rows:
            key = (
                row["document_id"],
                row["ocr_line_id"],
            )
            self.audit[key] = row

    def load_datasets(self):
        for document_id in DOCUMENTS:
            path = (
                WORKBENCH_DIR
                / f"document_{document_id}_review.csv"
            )

            rows = read_csv(path)

            for row in rows:
                status = row.get(
                    "validation_status", "pending"
                )

                if status not in STATUSES:
                    raise ValueError(
                        f"Unknown status {status} in {path}"
                    )

                key = (
                    row["document_id"],
                    row["ocr_line_id"],
                )

                if key not in self.audit:
                    raise ValueError(
                        f"Missing audit record: {key}"
                    )

            self.datasets[document_id] = rows

    # --------------------------------------------------------
    # Interface
    # --------------------------------------------------------

    def build_interface(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(
            top, text="Document:"
        ).pack(side="left")

        self.document_var = tk.StringVar()

        self.document_combo = ttk.Combobox(
            top,
            textvariable=self.document_var,
            values=DOCUMENTS,
            state="readonly",
            width=25,
        )
        self.document_combo.pack(
            side="left", padx=8
        )
        self.document_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.change_document(),
        )

        self.progress_label = ttk.Label(
            top, text="Progress: 0 / 0"
        )
        self.progress_label.pack(
            side="left", padx=25
        )

        ttk.Button(
            top,
            text="Save current line",
            command=self.save_current,
        ).pack(side="right", padx=5)

        main = ttk.PanedWindow(
            self.root, orient="horizontal"
        )
        main.pack(
            fill="both", expand=True, padx=10, pady=5
        )

        # Left side: list of lines.
        left = ttk.Frame(main, padding=5)
        main.add(left, weight=1)

        ttk.Label(
            left, text="OCR lines"
        ).pack(anchor="w")

        list_frame = ttk.Frame(left)
        list_frame.pack(
            fill="both", expand=True, pady=5
        )

        self.line_list = tk.Listbox(
            list_frame,
            width=38,
            font=("Consolas", 9),
            exportselection=False,
        )

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.line_list.yview,
        )

        self.line_list.configure(
            yscrollcommand=scrollbar.set
        )

        self.line_list.pack(
            side="left", fill="both", expand=True
        )
        scrollbar.pack(side="right", fill="y")

        self.line_list.bind(
            "<<ListboxSelect>>",
            self.select_line,
        )

        # Right side: images and annotation fields.
        right = ttk.Frame(main, padding=10)
        main.add(right, weight=4)

        image_frame = ttk.Frame(right)
        image_frame.pack(fill="x", expand=False)

        page_frame = ttk.LabelFrame(
            image_frame,
            text="Original document page",
            padding=5,
        )
        page_frame.pack(
            side="left", fill="both",
            expand=True, padx=(0, 5)
        )

        self.page_label = ttk.Label(page_frame)
        self.page_label.pack(
            fill="both", expand=True
        )

        crop_frame = ttk.LabelFrame(
            image_frame,
            text="Detected line crop (preview only)",
            padding=5,
        )
        crop_frame.pack(
            side="left", fill="both",
            expand=True, padx=(5, 0)
        )

        self.crop_label = ttk.Label(
            crop_frame,
            anchor="center",
        )
        self.crop_label.pack(
            fill="both", expand=True
        )

        details = ttk.LabelFrame(
            right,
            text="Text verification",
            padding=10,
        )
        details.pack(
            fill="x", pady=10
        )

        ttk.Label(
            details, text="OCR prediction:"
        ).pack(anchor="w")

        self.prediction_label = ttk.Label(
            details,
            text="",
            wraplength=850,
            font=("Arial", 11),
        )
        self.prediction_label.pack(
            anchor="w", pady=(2, 8)
        )

        ttk.Button(
            details,
            text="Copy prediction into transcription field",
            command=self.use_prediction,
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            details,
            text="Verified transcription (type what is printed):",
        ).pack(anchor="w")

        self.ground_truth = tk.Text(
            details,
            height=3,
            wrap="word",
            font=("Arial", 12),
        )
        self.ground_truth.pack(
            fill="x", pady=5
        )

        status_frame = ttk.Frame(details)
        status_frame.pack(fill="x", pady=5)

        ttk.Label(
            status_frame, text="Validation status:"
        ).pack(side="left")

        self.status_var = tk.StringVar(
            value="pending"
        )

        self.status_combo = ttk.Combobox(
            status_frame,
            textvariable=self.status_var,
            values=STATUSES,
            state="readonly",
            width=18,
        )
        self.status_combo.pack(
            side="left", padx=8
        )

        ttk.Label(
            details, text="Reviewer notes:"
        ).pack(anchor="w")

        self.notes = tk.Text(
            details,
            height=2,
            wrap="word",
            font=("Arial", 10),
        )
        self.notes.pack(
            fill="x", pady=5
        )

        buttons = ttk.Frame(details)
        buttons.pack(fill="x", pady=5)

        ttk.Button(
            buttons,
            text="← Previous",
            command=self.previous_line,
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons,
            text="Save and next →",
            command=self.save_and_next,
        ).pack(side="left", padx=3)

        ttk.Button(
            buttons,
            text="Next without saving →",
            command=self.next_line,
        ).pack(side="left", padx=3)

        self.info_label = ttk.Label(
            right,
            text="",
            foreground="gray",
        )
        self.info_label.pack(anchor="w")

    # --------------------------------------------------------
    # Document and line navigation
    # --------------------------------------------------------

    def change_document(self):
        if self.current_document is not None:
            if not self.save_current(silent=True):
                return

        document_id = self.document_var.get()

        if document_id not in self.datasets:
            return

        self.current_document = document_id
        self.current_index = None

        self.line_list.delete(0, tk.END)

        rows = self.datasets[document_id]

        for row in rows:
            status = row["validation_status"]
            line_id = row["ocr_line_id"]

            self.line_list.insert(
                tk.END,
                f"[{status[:3].upper()}] {line_id}",
            )

        self.update_progress()

        if rows:
            self.show_line(0)

    def select_line(self, event=None):
        if self.loading:
            return

        selection = self.line_list.curselection()

        if not selection:
            return

        new_index = selection[0]

        if new_index == self.current_index:
            return

        if self.current_index is not None:
            if not self.save_current(silent=True):
                self.restore_selection()
                return

        self.show_line(new_index)

    def restore_selection(self):
        if self.current_index is not None:
            self.line_list.selection_clear(0, tk.END)
            self.line_list.selection_set(
                self.current_index
            )
            self.line_list.see(self.current_index)

    def show_line(self, index):
        rows = self.datasets[self.current_document]

        if index < 0 or index >= len(rows):
            return

        self.loading = True
        self.current_index = index

        row = rows[index]
        line_id = row["ocr_line_id"]
        document_id = self.current_document

        self.line_list.selection_clear(0, tk.END)
        self.line_list.selection_set(index)
        self.line_list.see(index)

        self.prediction_label.configure(
            text=row.get("predicted_text", "")
        )

        self.ground_truth.delete("1.0", tk.END)
        self.ground_truth.insert(
            "1.0", row.get("ground_truth_text", "")
        )

        self.status_var.set(
            row.get("validation_status", "pending")
        )

        self.notes.delete("1.0", tk.END)
        self.notes.insert(
            "1.0", row.get("reviewer_notes", "")
        )

        self.display_images(document_id, line_id)

        audit_row = self.audit[
            (document_id, line_id)
        ]

        confidence = audit_row.get(
            "ocr_line_confidence", ""
        )

        self.info_label.configure(
            text=(
                f"Document: {document_id} | "
                f"Line: {line_id} | "
                f"Position: {index + 1}/{len(rows)} | "
                f"OCR confidence: {confidence}"
            )
        )

        self.loading = False

    # --------------------------------------------------------
    # Image display
    # --------------------------------------------------------

    def display_images(self, document_id, line_id):
        if (
            self.current_image is None
            or self.current_image_path != document_id
        ):
            if self.current_image is not None:
                self.current_image.close()

            image_path = find_tiff(document_id)

            with Image.open(image_path) as source:
                self.current_image = source.convert("RGB")

            self.current_image_path = document_id

        image = self.current_image
        audit_row = self.audit[
            (document_id, line_id)
        ]

        x1 = float(audit_row["ocr_x1"])
        y1 = float(audit_row["ocr_y1"])
        x2 = float(audit_row["ocr_x2"])
        y2 = float(audit_row["ocr_y2"])

        width, height = image.size

        left = max(0, int(x1))
        top = max(0, int(y1))
        right = min(width, int(x2 + 0.999))
        bottom = min(height, int(y2 + 0.999))

        if right <= left or bottom <= top:
            raise ValueError(
                f"Invalid crop coordinates for {line_id}"
            )

        # Full page with the detected line highlighted.
        page_preview = image.copy()
        draw = ImageDraw.Draw(page_preview)

        draw.rectangle(
            (left, top, right, bottom),
            outline="red",
            width=max(2, width // 300),
        )

        self.page_photo = load_font_image(
        page_preview, 500, 500
        )

        self.page_label.configure(
            image=self.page_photo
        )

        # Add visual-only context around the detected line.
        # These margins do NOT change stored coordinates.
        preview_margin = 4

        crop_left = max(0, left - preview_margin)
        crop_top = max(0, top - preview_margin)
        crop_right = min(width, right + preview_margin)
        crop_bottom = min(height, bottom + preview_margin)

        crop = image.crop(
            (
                crop_left,
                crop_top,
                crop_right,
                crop_bottom,
            )
        )

        # Enlarge small text for easier reading.
        scale = min(
            5,
            max(1, 650 // max(1, crop.width)),
        )

        enlarged = crop.resize(
            (
                crop.width * scale,
                crop.height * scale,
            ),
            Image.Resampling.LANCZOS,
        )

        self.crop_photo = load_font_image(
        enlarged, 650, 180
)

        self.crop_label.configure(
            image=self.crop_photo
        )

        page_preview.close()
        crop.close()

    # --------------------------------------------------------
    # Save and navigation
    # --------------------------------------------------------

    def use_prediction(self):
        if self.current_index is None:
            return

        row = self.datasets[
            self.current_document
        ][self.current_index]

        self.ground_truth.delete("1.0", tk.END)
        self.ground_truth.insert(
            "1.0", row.get("predicted_text", "")
        )

    def save_current(self, silent=False):
        if (
            self.current_document is None
            or self.current_index is None
        ):
            return True

        rows = self.datasets[self.current_document]
        row = rows[self.current_index]

        ground_truth = self.ground_truth.get(
            "1.0", "end-1c"
        ).strip()

        status = self.status_var.get()

        notes = self.notes.get(
            "1.0", "end-1c"
        ).strip()

        if status in TRAINING_STATUSES and not ground_truth:
            if not silent:
                messagebox.showwarning(
                    "Transcription required",
                    "Enter the verified printed text before "
                    "using a training-eligible status.",
                )
            return False

        if status not in STATUSES:
            messagebox.showerror(
                "Invalid status",
                "Choose a valid annotation status.",
            )
            return False

        row["ground_truth_text"] = ground_truth
        row["validation_status"] = status
        row["reviewer_notes"] = notes

        path = (
            WORKBENCH_DIR
            / f"document_{self.current_document}_review.csv"
        )

        try:
            write_csv_atomic(path, rows)
        except Exception as error:
            messagebox.showerror(
                "Save failed", str(error)
            )
            return False

        self.refresh_list_item()
        self.update_progress()

        if not silent:
            self.root.title(
                "OCR Human Annotation Review — Saved"
            )

        return True

    def refresh_list_item(self):
        if self.current_index is None:
            return

        row = self.datasets[
            self.current_document
        ][self.current_index]

        status = row["validation_status"]
        line_id = row["ocr_line_id"]

        self.line_list.delete(self.current_index)
        self.line_list.insert(
            self.current_index,
            f"[{status[:3].upper()}] {line_id}",
        )

        self.line_list.selection_set(
            self.current_index
        )

    def save_and_next(self):
        if self.save_current():
            self.next_line()

    def next_line(self):
        if self.current_index is None:
            return

        if self.current_index + 1 < len(
            self.datasets[self.current_document]
        ):
            self.show_line(self.current_index + 1)

    def previous_line(self):
        if self.current_index is None:
            return

        if self.current_index > 0:
            self.show_line(self.current_index - 1)

    # --------------------------------------------------------
    # Progress and exit
    # --------------------------------------------------------

    def update_progress(self):
        rows = self.datasets[self.current_document]

        completed = sum(
            1 for row in rows
            if row["validation_status"] != "pending"
        )

        self.progress_label.configure(
            text=(
                f"Progress: {completed}/{len(rows)} "
                f"reviewed"
            )
        )

    def close_application(self):
        if not self.save_current(silent=True):
            messagebox.showwarning(
                "Not saved",
                "The current line could not be saved. "
                "Please correct the issue before closing.",
            )
            return

        if self.current_image is not None:
            self.current_image.close()

        self.root.destroy()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()

    try:
        app = AnnotationApp(root)
        root.mainloop()

    except Exception as error:
        messagebox.showerror(
            "Application error", str(error)
        )
        raise
