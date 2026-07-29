"""
face_recognizer.py — InsightFace-based face embedding module for KinderSort.

Extracts 512-dimensional face feature vectors using InsightFace ArcFace models.
Returns embedding vectors only.
"""

import logging

import numpy as np
import insightface
from insightface.app import FaceAnalysis

logger = logging.getLogger("kindersort")


class InsightFaceRecognizer:
    """InsightFace-based face recognizer returning 512-dimensional feature vectors."""

    CROP_MARGIN = 0.25
    """Extra context around a detector box so InsightFace can re-detect the face."""

    def __init__(
        self,
        model_name: str = "buffalo_l",
        providers: list[str] | None = None,
        ctx_id: int = -1,
    ) -> None:
        """Initialize the InsightFace recognition model.

        Args:
            model_name: InsightFace model bundle name (default: "buffalo_l").
            providers: ONNXRuntime execution providers (default: CPU execution).
            ctx_id: Device ID (-1 for CPU execution, >= 0 for GPU).
        """
        self.model_name = model_name
        self.providers = providers or ["CPUExecutionProvider"]
        self.ctx_id = ctx_id
        self._app: FaceAnalysis | None = None

    def _get_app(self) -> FaceAnalysis:
        """Lazy load the InsightFace FaceAnalysis application."""
        if self._app is None:
            logger.info("Initializing InsightFace model (%s) on CPU", self.model_name)
            app = FaceAnalysis(
                name=self.model_name,
                providers=self.providers,
                allowed_modules=["detection", "recognition"],
            )
            app.prepare(ctx_id=self.ctx_id, det_size=(640, 640))
            self._app = app
        return self._app

    def extract_embedding(self, face_crop: np.ndarray) -> np.ndarray | None:
        """Extract a 512-d normalized face feature vector from a cropped face image.

        Args:
            face_crop: Cropped face image region as a BGR/RGB numpy array.

        Returns:
            512-dimensional normalized float32 numpy vector, or None if extraction fails.
        """
        try:
            if face_crop is None or face_crop.size == 0:
                return None

            app = self._get_app()
            faces = app.get(face_crop)
            if not faces:
                logger.debug("No face found while extracting an embedding from the crop")
                return None

            # The crop includes a safety margin. Prefer the face nearest its
            # centre so a nearby person in a group photo is not encoded instead.
            crop_center = np.array(
                [face_crop.shape[1] / 2, face_crop.shape[0] / 2], dtype=np.float32
            )
            selected_face = min(
                faces,
                key=lambda face: float(
                    np.linalg.norm(
                        ((face.bbox[:2] + face.bbox[2:]) / 2) - crop_center
                    )
                ),
            )
            logger.debug(
                "Embedding face selected from %d candidate(s): confidence=%.3f",
                len(faces),
                float(selected_face.det_score),
            )
            embedding = selected_face.embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except Exception as exc:
            logger.error("Failed to extract embedding from crop: %s", exc)
            return None

    def extract_embeddings_for_boxes(
        self,
        image: np.ndarray,
        bounding_boxes: list[tuple[int, int, int, int]],
    ) -> list[np.ndarray]:
        """Extract 512-d normalized face embeddings for each bounding box in an image.

        Args:
            image: Full image numpy array (BGR format).
            bounding_boxes: List of (x1, y1, x2, y2) bounding box tuples.

        Returns:
            List of 512-dimensional normalized float32 numpy vectors.
        """
        embeddings: list[np.ndarray] = []
        if image is None or image.size == 0 or not bounding_boxes:
            return embeddings

        h, w = image.shape[:2]
        for x1, y1, x2, y2 in bounding_boxes:
            # InsightFace's embedding API performs face detection again on this
            # crop. A detector box alone is often too tight for that second
            # pass, so retain 25% surrounding context before cropping.
            margin_x = int((x2 - x1) * self.CROP_MARGIN)
            margin_y = int((y2 - y1) * self.CROP_MARGIN)
            x1_c, y1_c = max(0, x1 - margin_x), max(0, y1 - margin_y)
            x2_c, y2_c = min(w, x2 + margin_x), min(h, y2 + margin_y)
            face_crop = image[y1_c:y2_c, x1_c:x2_c]

            if face_crop.size == 0:
                logger.warning(
                    "Skipping empty face crop from box (%d, %d, %d, %d)",
                    x1,
                    y1,
                    x2,
                    y2,
                )
                continue

            logger.info(
                "Extracting embedding from expanded face crop: original=%s crop=%s",
                (x1, y1, x2, y2),
                (x1_c, y1_c, x2_c, y2_c),
            )

            emb = self.extract_embedding(face_crop)
            if emb is not None:
                embeddings.append(emb)

        return embeddings

    @staticmethod
    def compute_cosine_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate Cosine distance between two normalized 512-d face embeddings.

        Distance = 1.0 - CosineSimilarity. Range: 0.0 (identical) to 2.0 (opposite).

        Args:
            emb1: 512-d normalized numpy float array.
            emb2: 512-d normalized numpy float array.

        Returns:
            Cosine distance float value.
        """
        cosine_sim = float(np.dot(emb1, emb2))
        return 1.0 - cosine_sim
