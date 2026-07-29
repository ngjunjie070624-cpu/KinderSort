# KinderSort — Student Photo Organiser

[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/lerlerchan/KinderSort/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CPU Only](https://img.shields.io/badge/GPU-not_required-orange)](https://github.com/lerlerchan/KinderSort)
[![Release](https://img.shields.io/github/v/release/lerlerchan/KinderSort?color=blue&logo=github)](https://github.com/lerlerchan/KinderSort/releases)

[中文说明 (简体)](README.zh-CN.md)

KinderSort is a desktop app for kindergarten teachers. It scans classroom event photos, matches student faces against a reference folder, and copies each photo into the correct student's folder automatically — no coding knowledge required.

---

## 1. Project Overview

Sorting hundreds of event photos by hand and figuring out which child appears in which photo is slow and error-prone. KinderSort automates this with a local, CPU-only face detection and recognition pipeline, wrapped in a simple point-and-click interface so a non-technical teacher can run it by double-clicking one file.

---

## 2. Features

| Feature | Detail |
|---|---|
| Automatic sorting | Detects and recognises student faces, copies matching photos into per-student folders |
| Group photo support | One photo is copied to every student it contains |
| CPU-only | Runs on any Windows PC without a GPU |
| Modern GUI | CustomTkinter interface with Light/Dark mode, Windows 11-styled cards |
| Safe operation | Files are **copied**, never moved or deleted — originals are always intact |
| Live performance panel | Real-time CPU%, memory, elapsed time, and images/sec while sorting (via `psutil`) |
| Audit trail | Detailed run log written to `kindersort_log.txt` in the output folder |
| Cancel-safe | Sorting can be cancelled mid-run; photos already processed are kept |

---

## 3. AI Architecture

```
 Reference photos ─┐
                    ├─▶ Face Detector (InsightFace SCRFD, YOLOv8 optional) ─▶ bounding boxes
 Event photos ──────┘
                                       │
                                       ▼
                     Face Recognizer (InsightFace ArcFace, buffalo_l)
                                       │
                            512-d normalized embedding
                                       │
                                       ▼
                 Cosine-distance match against each student's
                 reference embedding(s) — closest student under
                 the distance threshold (and clear of any near-tie) wins
                                       │
                                       ▼
                    Matched photo copied to Output/<StudentName>/
                    (multiple folders for group photos);
                    no match / no face → Output/_unmatched/
```

**Detection:** `face_detector.py` primarily uses InsightFace's SCRFD detector (CPU, ONNX Runtime backend). A YOLOv8 face-model path exists as an optional alternative — if the configured weights file isn't present or isn't a face-trained model, the code automatically falls back to SCRFD, so no manual configuration is required for the default setup.

**Recognition:** `face_recognizer.py` uses InsightFace's `buffalo_l` ArcFace model to produce a 512-dimensional, L2-normalized face embedding per detected face. Matching (`sorter.py`) compares each embedding to every stored student reference embedding via cosine distance, accepts the closest match under a fixed threshold, and rejects ambiguous near-ties between two students.

---

## 4. Technologies Used

[![OpenCV](https://img.shields.io/badge/OpenCV-image_processing-red)](https://opencv.org/)
[![InsightFace](https://img.shields.io/badge/InsightFace-face_recognition-blueviolet)](https://github.com/deepinsight/insightface)
[![Ultralytics YOLOv8](https://img.shields.io/badge/YOLOv8-optional_detector-yellow)](https://github.com/ultralytics/ultralytics)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-CPU-lightgrey)](https://onnxruntime.ai/)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-GUI-1E90FF)](https://github.com/TomSchimansky/CustomTkinter)
[![psutil](https://img.shields.io/badge/psutil-resource_monitoring-green)](https://github.com/giampaolo/psutil)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-packaging-purple)](https://pyinstaller.org/)

| Component | Library |
|---|---|
| Face detection | InsightFace SCRFD (default) / Ultralytics YOLOv8 (optional) |
| Face recognition | InsightFace ArcFace (`buffalo_l`), via ONNX Runtime (CPU) |
| Image handling | OpenCV, Pillow |
| GUI | CustomTkinter |
| Resource monitoring | psutil |
| Packaging | PyInstaller |
| Language | Python 3.10+ |

---

## 5. Installation Guide

```bash
git clone https://github.com/lerlerchan/KinderSort.git
cd KinderSort
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

> **First run needs internet, once.** InsightFace downloads the `buffalo_l` model (~300 MB) to `~/.insightface/models` the first time the app runs. After that first download, sorting itself runs fully offline. This is a correction from earlier documentation, which described the app as offline from the very first launch.

---

## 6. Requirements

- Windows 10/11 (development also works on Ubuntu for the source version)
- Python 3.10+ (only needed if running from source — not needed for the packaged `.exe`)
- No GPU required — CPU only
- ~2 GB free disk space (model weights + dependencies)
- Internet connection for the one-time model download described above

See [`requirements.txt`](requirements.txt) for pinned package versions.

---

## 7. How to Run

**From source:**
```bash
python main.py
```

**Packaged app (teachers):**
1. Download `KinderSort.exe` from the [Releases](https://github.com/lerlerchan/KinderSort/releases) page
2. Double-click `KinderSort.exe`
3. Select the Reference, Classroom, and Output folders
4. Click **Start Sorting**
5. Review the summary and open the Output folder

Full illustrated guide: [`guidebook.md`](guidebook.md)

**Build the `.exe` yourself:**
```bash
pip install pyinstaller
pyinstaller KinderSort.spec
# Output: dist/KinderSort.exe
```

---

## 8. Folder Structure

```
kindersort/
├── main.py              ← GUI entry point (CustomTkinter)
├── sorter.py             ← PhotoSorter: reference loading + sort pipeline
├── face_detector.py      ← Face detection (SCRFD / optional YOLOv8)
├── face_recognizer.py    ← Face embedding + cosine-distance matching
├── utils.py               ← File helpers, naming, logging setup
├── perf_monitor.py        ← psutil-based CPU/RAM monitoring for the GUI panel
├── requirements.txt       ← Pinned dependencies
├── KinderSort.spec        ← PyInstaller build configuration
├── README.md               ← This file
├── README.zh-CN.md         ← 简体中文说明
├── guidebook.md             ← Teacher-facing illustrated guide
└── dist/
    └── KinderSort.exe        ← Packaged output (after building)
```

**At runtime, the teacher selects three folders (not part of the repo):**

```
Reference/            Classroom/                Output/
  Ali.jpg               Sports_Day/               Ali/
  Siti.png               Concert/                 Siti/
  Kumar.jpeg              Field_Trip/              _unmatched/
                                                     kindersort_log.txt
```

---

## 9. Screenshots

| Step | Screenshot |
|---|---|
| App launch | `guidebook_assets/01_launch.png` |
| Reference folder selected | `guidebook_assets/02_reference_selected.png` |
| Classroom folder selected | `guidebook_assets/03_events_selected.png` |
| All folders ready | `guidebook_assets/04_all_folders_set.png` |
| Sorting in progress | `guidebook_assets/05_sorting_in_progress.png` |
| Sorting complete | `guidebook_assets/06_sorting_complete.png` |

*(Placeholders — regenerate with `quick_screenshots.py` against the current GUI before submission, since the interface has changed since these were last captured.)*

---

## 10. Performance Summary

Measured via the built-in System Performance panel (`psutil`), CPU-only, no GPU:

| Metric | Typical value* |
|---|---|
| CPU usage while sorting | ~15–25% of one core (varies by image size/count) |
| Peak memory | ~250–300 MB |
| Throughput | roughly 0.3–1.5 sec/image, depending on resolution and face count |

\* *Figures are indicative from development testing, not a guaranteed SLA — actual numbers depend on the teacher's hardware and photo resolution. Run a batch and check the "Performance" section of the completion summary for real numbers on the target machine.*

---

## 11. Future Improvements

- Bundle the InsightFace `buffalo_l` model weights into the PyInstaller build so the very first run is offline too (currently requires one internet-connected run to download them)
- Multi-scale re-detection pass specifically for reference photos, to reduce missed faces in group reference shots
- Encourage/enforce multiple reference photos per student (already supported via `Reference/StudentName/*.jpg` subfolders) directly from the GUI, rather than relying on documentation alone
- Optional CSV/Excel export of the match summary alongside the text log
- Basic automated tests around `sorter.py`'s matching logic (currently manually verified)

---

## 12. License

No license file is currently included in this repository. Add a `LICENSE` file (e.g. MIT) before public distribution if you intend for others to reuse this code — until then, all rights are reserved by default under copyright law.

---

## Developer Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
