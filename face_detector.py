"""
face_detector.py — Face detection module for KinderSort.

Detects faces in images using YOLOv8 or InsightFace SCRFD fallback,
returning bounding box coordinates (x1, y1, x2, y2).
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from ultralytics import YOLO

logger = logging.getLogger("kindersort")


class YOLOFaceDetector:
    """Face detector using YOLOv8 or InsightFace SCRFD fallback."""

    def __init__(
        self,
        model_path: str | Path = "yolov8n-face.pt",
        conf_threshold: float = 0.25,
    ) -> None:
        """Initialize the face detector.

        Args:
            model_path: Path or name of the YOLOv8 face model weights file.
            conf_threshold: Minimum confidence score threshold for detection.
        """
        self.model_path = str(model_path)
        self.conf_threshold = conf_threshold
        self.det_size = (704, 704)
        self.nms_threshold = 0.45
        self._yolo_model: YOLO | None = None
        self._insight_app: FaceAnalysis | None = None
        self._use_insight_fallback = False

    def _get_yolo_model(self) -> YOLO | None:
        """Lazy load YOLO model if weights exist; otherwise trigger fallback."""
        if self._use_insight_fallback:
            return None

        if self._yolo_model is None:
            if Path(self.model_path).exists():
                try:
                    logger.info("Loading YOLO face detection model from %s", self.model_path)
                    self._yolo_model = YOLO(self.model_path)
                    class_names = self._yolo_model.names
                    names = (
                        class_names.values()
                        if isinstance(class_names, dict)
                        else class_names
                    )
                    if not any(str(name).strip().lower() == "face" for name in names):
                        logger.warning(
                            "YOLO model '%s' is not a face model (classes: %s). "
                            "Using InsightFace SCRFD instead.",
                            self.model_path,
                            list(names),
                        )
                        self._yolo_model = None
                        self._use_insight_fallback = True
                except Exception as exc:
                    logger.warning("Failed to load YOLO model (%s), using InsightFace fallback: %s", self.model_path, exc)
                    self._use_insight_fallback = True
            else:
                logger.info("YOLO model '%s' not found locally. Using InsightFace SCRFD detector.", self.model_path)
                self._use_insight_fallback = True

        return self._yolo_model

    def _get_insight_app(self) -> FaceAnalysis:
        """Lazy load InsightFace SCRFD detector as robust fallback."""
        if self._insight_app is None:
            logger.info("Initializing InsightFace SCRFD face detector...")
            app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
                allowed_modules=["detection"],
            )
            # 704px improves recall for smaller background faces while adding
            # only about 21% more pixels than the previous 640px input.
            app.prepare(
                ctx_id=-1,
                det_thresh=self.conf_threshold,
                det_size=self.det_size,
            )
            app.det_model.prepare(ctx_id=-1, nms_thresh=self.nms_threshold)
            logger.info(
                "SCRFD settings: confidence=%.2f input=%s NMS=%.2f",
                self.conf_threshold,
                self.det_size,
                self.nms_threshold,
            )
            self._insight_app = app
        return self._insight_app

    def detect_faces(
        self, image: str | Path | np.ndarray
    ) -> list[tuple[int, int, int, int]]:
        """Detect all faces in an image and return bounding boxes.

        Args:
            image: Path to an image file (str or Path) OR an OpenCV BGR numpy
                array.  The rest of KinderSort converts Pillow RGB images to
                BGR before calling this method.

        Returns:
            List of bounding box tuples in (x1, y1, x2, y2) format.
        """
        try:
            boxes: list[tuple[int, int, int, int]] = []

            # 1. Try YOLO if weights are available
            yolo = self._get_yolo_model()
            if yolo is not None:
                logger.info("Detector: YOLO face model (%s)", self.model_path)
                src = str(image) if isinstance(image, Path) else image
                results = yolo.predict(source=src, conf=self.conf_threshold, verbose=False)
                if results:
                    for result in results:
                        if result.boxes is not None and len(result.boxes) > 0:
                            for box in result.boxes:
                                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                                confidence = float(box.conf[0].cpu().item())
                                detected_box = self._valid_box(xyxy, result.orig_shape)
                                if detected_box is not None:
                                    boxes.append(detected_box)
                                    logger.info(
                                        "YOLO face: confidence=%.3f box=%s",
                                        confidence,
                                        detected_box,
                                    )
                    logger.info("YOLO detected %d face(s)", len(boxes))
                    if boxes:
                        return boxes

            # 2. Fallback to InsightFace SCRFD detector
            img_arr = None
            if isinstance(image, (str, Path)):
                img_arr = cv2.imread(str(image))
            elif isinstance(image, np.ndarray):
                img_arr = image

            if img_arr is not None and img_arr.size > 0:
                logger.info("Detector: InsightFace SCRFD fallback")
                app = self._get_insight_app()
                detector_image = self._enhance_low_contrast_image(img_arr)
                faces = app.get(detector_image)
                for face in faces:
                    detected_box = self._valid_box(face.bbox, img_arr.shape[:2])
                    if detected_box is not None:
                        boxes.append(detected_box)
                        logger.info(
                            "SCRFD face: confidence=%.3f box=%s",
                            float(face.det_score),
                            detected_box,
                        )
                logger.info("SCRFD detected %d face(s)", len(boxes))
            else:
                logger.warning("Face detection received an empty or unreadable image")

            return boxes

        except Exception as exc:
            logger.error("Error during face detection: %s", exc)
            return []

    @staticmethod
    def _enhance_low_contrast_image(image: np.ndarray) -> np.ndarray:
        """Apply CLAHE only when a dark or low-contrast image needs it."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(gray.mean())
        contrast = float(gray.std())
        if brightness >= 70.0 and contrast >= 35.0:
            return image

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, channel_a, channel_b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = cv2.merge((clahe.apply(lightness), channel_a, channel_b))
        logger.info(
            "Applied CLAHE before SCRFD (brightness=%.1f contrast=%.1f)",
            brightness,
            contrast,
        )
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    @staticmethod
    def _valid_box(
        bbox: np.ndarray, image_shape: tuple[int, int]
    ) -> tuple[int, int, int, int] | None:
        """Clamp an ``(x1, y1, x2, y2)`` box and reject empty crops."""
        height, width = image_shape
        x1, y1, x2, y2 = (int(value) for value in bbox[:4])
        x1, x2 = max(0, x1), min(width, x2)
        y1, y2 = max(0, y1), min(height, y2)
        if x2 <= x1 or y2 <= y1:
            logger.warning("Ignoring invalid face box: (%d, %d, %d, %d)", x1, y1, x2, y2)
            return None
        return x1, y1, x2, y2
