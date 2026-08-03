"""
sorter.py — Face recognition logic for KinderSort.

PhotoSorter loads reference encodings and sorts event photos into per-student
output folders using YOLOv8n face detection and InsightFace face recognition.
All processing is CPU-only (no GPU required).
"""

import logging
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from face_detector import YOLOFaceDetector
from face_recognizer import InsightFaceRecognizer
from utils import (
    build_output_filename,
    collect_event_images,
    is_image_file,
    safe_copy,
)

# Startup optimization: one shared detector/recognizer pair warmed in a
# background thread so PhotoSorter reuses preloaded weights instead of
# constructing (and loading) fresh instances on every Start click.
_shared_detector: YOLOFaceDetector | None = None
_shared_recognizer: InsightFaceRecognizer | None = None


def preload_ai_models() -> tuple[YOLOFaceDetector, InsightFaceRecognizer]:
    """Load YOLOv8, InsightFace, and ONNX Runtime once for reuse across runs.

    Called from main.py's background startup thread after the GUI is visible.
    Imports onnxruntime here so its native DLLs are not loaded on the main
    thread before the window appears. CPU-only providers are unchanged.
    """
    global _shared_detector, _shared_recognizer
    import onnxruntime  # noqa: F401 — warm ONNX Runtime in the background thread

    if _shared_detector is None:
        _shared_detector = YOLOFaceDetector()
    if _shared_recognizer is None:
        _shared_recognizer = InsightFaceRecognizer()
    _shared_detector.preload_models()
    _shared_recognizer.preload_models()
    return _shared_detector, _shared_recognizer


class PhotoSorter:
    """Encapsulates the full sort pipeline from reference loading to file copying.

    Usage::

        sorter = PhotoSorter(reference_folder, events_folder, output_folder, logger)
        skipped_names = sorter.load_references()   # sync, may show warnings
        summary = sorter.sort_all(progress_cb, cancelled_cb)
    """

    DISTANCE_THRESHOLD = 0.60
    """Maximum ArcFace cosine distance to accept a student match.

    Slightly relaxed to reduce false unmatched results when lighting, pose,
    or expression differ from the reference image. This is a moderate
    adjustment to improve recall without making matching overly permissive.
    """

    AMBIGUITY_MARGIN = 0.01
    """Minimum gap between the best and second-best student distances.

    Reduced slightly so a candidate with a marginally better distance is not
    rejected solely because the runner-up is close.
    """

    MAX_IMAGE_DIMENSION = 800
    """Longest side in pixels after resizing for face detection (performance)."""

    def __init__(
        self,
        reference_folder: Path,
        events_folder: Path,
        output_folder: Path,
        logger: logging.Logger,
    ) -> None:
        """Store folder paths and logger; initialise detector, recognizer, and empty encoding dict."""
        self.reference_folder = reference_folder
        self.events_folder = events_folder
        self.output_folder = output_folder
        self.logger = logger
        # Each student can have several reference images while root-level
        # ``Student Name.jpg`` files continue to work exactly as before.
        self._student_encodings: dict[str, list[np.ndarray]] = {}

        # Reuse models preloaded at startup when available; otherwise fall
        # back to the original per-instance lazy loaders (unchanged logic).
        self.detector = _shared_detector if _shared_detector is not None else YOLOFaceDetector()
        self.recognizer = (
            _shared_recognizer if _shared_recognizer is not None else InsightFaceRecognizer()
        )

    # ------------------------------------------------------------------
    # Reference loading
    # ------------------------------------------------------------------

    def load_references(
        self,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[str]:
        """Encode every reference photo and store by student name.

        Root-level images use their filename as the student name (for example,
        ``Ali.jpg``). Images inside ``Ali/`` are all treated as references for
        Ali, allowing multiple poses without changing the existing layout.

        Args:
            progress_callback: Optional callable with ``(current, total, name)``
                called after each student is processed so the GUI can update.

        Returns:
            List of student names whose reference photo had no detectable face.
            Callers should show a warning for each name in this list.
        """
        no_face_names: list[str] = []

        # Subfolders allow several references per student; existing images at
        # the root stay compatible and still use their filename as the name.
        reference_images = sorted(
            p
            for p in self.reference_folder.rglob("*")
            if p.is_file() and is_image_file(p)
        )

        if not reference_images:
            self.logger.warning("No reference images found in %s", self.reference_folder)
            return no_face_names

        total = len(reference_images)
        reference_students: set[str] = set()
        for current, ref_path in enumerate(reference_images, start=1):
            student_name = (
                ref_path.parent.name
                if ref_path.parent != self.reference_folder
                else ref_path.stem
            )
            reference_students.add(student_name)
            if progress_callback:
                progress_callback(current, total, student_name)
            try:
                rgb_image = self._load_and_resize(ref_path)
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)

                # InsightFace/SCRFD is an OpenCV model and expects BGR input.
                boxes = self.detector.detect_faces(bgr_image)
                if not boxes:
                    self.logger.warning(
                        "No face detected in reference photo for %s (%s)",
                        student_name,
                        ref_path.name,
                    )
                    continue

                if len(boxes) > 1:
                    # ROOT CAUSE (students wrongly "Unmatched"): boxes[0] is
                    # whatever order the detector happens to emit — not
                    # necessarily the student. If a sibling, teacher, or
                    # photobomber appears in the reference photo and lands
                    # at index 0, the student's stored embedding is actually
                    # the *wrong person's* face, and every real photo of the
                    # student then fails to match. In a reference photo the
                    # intended subject is almost always the largest face
                    # (closest to camera / most prominent), so we select by
                    # box area instead of detector order. This is a
                    # heuristic, not a guarantee — the "Multiple faces"
                    # warning still fires so a teacher can crop a cleaner
                    # reference photo if needed.
                    box_areas = [
                        (b, (b[2] - b[0]) * (b[3] - b[1])) for b in boxes
                    ]
                    box_areas.sort(key=lambda item: item[1], reverse=True)
                    chosen_box = box_areas[0][0]
                    self.logger.warning(
                        "Multiple faces (%d) in reference photo for %s — "
                        "using largest face (area=%dpx² of %s) as the "
                        "student; other boxes: %s",
                        len(boxes),
                        student_name,
                        box_areas[0][1],
                        chosen_box,
                        [f"{b}:{a}px²" for b, a in box_areas[1:]],
                    )
                else:
                    chosen_box = boxes[0]

                encodings = self.recognizer.extract_embeddings_for_boxes(
                    bgr_image, [chosen_box]
                )

                if not encodings:
                    self.logger.warning(
                        "Could not extract face embedding for %s (%s)",
                        student_name,
                        ref_path.name,
                    )
                    continue

                student_references = self._student_encodings.setdefault(student_name, [])
                student_references.append(encodings[0])
                self.logger.info(
                    "Loaded reference for %s (%d embedding(s))",
                    student_name,
                    len(student_references),
                )

            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Could not read reference photo %s: %s", ref_path.name, exc
                )

        no_face_names = sorted(
            name for name in reference_students if name not in self._student_encodings
        )
        total_embeddings = sum(
            len(embeddings) for embeddings in self._student_encodings.values()
        )
        self.logger.info(
            "Loaded %d student(s) with %d reference embedding(s)",
            len(self._student_encodings),
            total_embeddings,
        )
        return no_face_names

    # ------------------------------------------------------------------
    # Main sort loop
    # ------------------------------------------------------------------

    def sort_all(
        self,
        progress_callback: Callable[[int, int, str], None],
        cancelled: Callable[[], bool],
    ) -> dict[str, int]:
        """Sort all event photos into per-student output subfolders.

        Processes one image at a time to keep RAM usage low. For each detected
        face in a photo the nearest student is identified; the photo is copied
        to every matched student folder (allowing group shots). Photos with no
        match or no face are copied to ``_unmatched/``.

        Args:
            progress_callback: Called with ``(current, total, filename)`` after
                each image so the GUI can update its progress bar.
            cancelled: Zero-arg callable; returns True if the user has cancelled.

        Returns:
            Dict with keys ``total``, ``matched``, ``unmatched``, ``skipped``.
        """
        images = collect_event_images(self.events_folder)
        total = len(images)

        counts = {"total": total, "matched": 0, "unmatched": 0, "skipped": 0}

        self.logger.info("Starting sort — %d images found", total)

        for current, (image_path, event_name) in enumerate(images, start=1):
            if cancelled():
                self.logger.info("Sort cancelled by user at image %d/%d", current, total)
                break

            progress_callback(current, total, image_path.name)

            output_filename = build_output_filename(event_name, image_path.name)

            try:
                rgb_image = self._load_and_resize(image_path)
                bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            except UnidentifiedImageError:
                self.logger.warning("Corrupted image, moving to _unmatched: %s", image_path.name)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1
                continue
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Could not open %s: %s — skipping", image_path.name, exc)
                counts["skipped"] += 1
                continue

            try:
                # Keep detection and recognition in OpenCV's BGR convention.
                boxes = self.detector.detect_faces(bgr_image)
                face_encodings = (
                    self.recognizer.extract_embeddings_for_boxes(bgr_image, boxes)
                    if boxes
                    else []
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Face detection failed for %s: %s", image_path.name, exc)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1
                continue

            if not face_encodings:
                if boxes:
                    self.logger.warning(
                        "Detector returned %d face box(es) for %s, but no embedding "
                        "could be extracted; sending to _unmatched",
                        len(boxes),
                        image_path.name,
                    )
                else:
                    self.logger.info("No face detected: %s → _unmatched", image_path.name)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1
                continue

            matched_students: set[str] = set()
            for encoding in face_encodings:
                match = self._match_face(encoding)
                if match:
                    matched_students.add(match)

            if matched_students:
                for student_name in matched_students:
                    dest_folder = self.output_folder / student_name
                    safe_copy(image_path, dest_folder, output_filename, self.logger)
                    self.logger.info(
                        "Matched %s → %s", image_path.name, student_name
                    )
                counts["matched"] += 1
            else:
                self.logger.info("No match: %s → _unmatched", image_path.name)
                safe_copy(image_path, self.output_folder / "_unmatched", output_filename, self.logger)
                counts["unmatched"] += 1

        self.logger.info(
            "Sort complete — total=%d matched=%d unmatched=%d skipped=%d",
            counts["total"],
            counts["matched"],
            counts["unmatched"],
            counts["skipped"],
        )
        return counts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_and_resize(self, image_path: Path) -> np.ndarray:
        """Open image with Pillow, resize if needed, and return as RGB numpy array.

        Resizing large images to at most MAX_IMAGE_DIMENSION on the longest side
        dramatically reduces detection time on CPU without meaningfully
        reducing recognition accuracy.

        Raises:
            UnidentifiedImageError: If Pillow cannot read the file format.
        """
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            longest = max(width, height)
            if longest > self.MAX_IMAGE_DIMENSION:
                scale = self.MAX_IMAGE_DIMENSION / longest
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.LANCZOS)
            return np.array(img)

    def _match_face(self, encoding: np.ndarray) -> str | None:
        """Find the closest student reference within the match threshold.

        Calculates cosine distance against every available reference, selects
        the closest result per student, and rejects ambiguous matches.

        Args:
            encoding: 512-d face feature vector.

        Returns:
            Student name string if a match is found, otherwise None.
        """
        if not self._student_encodings:
            return None

        # Score each student by their closest reference image. This keeps the
        # original one-image workflow and improves pose/lighting tolerance when
        # reference subfolders supply several embeddings for a student.
        student_distances: list[tuple[str, float]] = []
        for student_name, references in self._student_encodings.items():
            distance = min(
                InsightFaceRecognizer.compute_cosine_distance(reference, encoding)
                for reference in references
            )
            similarity = 1.0 - distance
            self.logger.debug(
                "Recognition candidate %s: similarity=%.4f distance=%.4f",
                student_name,
                similarity,
                distance,
            )
            student_distances.append((student_name, distance))

        student_distances.sort(key=lambda item: item[1])
        best_name, best_distance = student_distances[0]
        best_similarity = 1.0 - best_distance
        second_distance = (
            student_distances[1][1] if len(student_distances) > 1 else None
        )

        if best_distance > self.DISTANCE_THRESHOLD:
            self.logger.info(
                "Unmatched face: reason=distance similarity=%.4f distance=%.4f "
                "threshold=%.4f best_candidate=%s",
                best_similarity,
                best_distance,
                self.DISTANCE_THRESHOLD,
                best_name,
            )
            return None

        if (
            second_distance is not None
            and second_distance - best_distance < self.AMBIGUITY_MARGIN
        ):
            self.logger.info(
                "Unmatched face: reason=ambiguous best=%s distance=%.4f "
                "second_distance=%.4f margin=%.4f",
                best_name,
                best_distance,
                second_distance,
                self.AMBIGUITY_MARGIN,
            )
            return None

        self.logger.info(
            "Face matched to %s (similarity=%.4f distance=%.4f threshold=%.4f)",
            best_name,
            best_similarity,
            best_distance,
            self.DISTANCE_THRESHOLD,
        )
        return best_name