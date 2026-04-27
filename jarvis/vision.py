"""
===========================================================
J.A.R.V.I.S. — Vision Module
===========================================================
OpenCV + face_recognition + YOLOv8 + MediaPipe
Face detection/recognition, object detection, gestures.
===========================================================
"""

import io
import time
import logging
import threading
import numpy as np
from pathlib import Path
from typing import Callable, Optional
from jarvis.config import (
    CAMERA_INDEX, FACE_RECOGNITION_TOLERANCE,
    VISION_FPS, YOLO_MODEL, USER_TITLE
)

logger = logging.getLogger("jarvis.vision")


class VisionSystem:
    """Computer vision: face recognition, object detection, gestures."""

    def __init__(self, memory=None, on_face_detected: Callable = None):
        self.memory = memory
        self.on_face_detected = on_face_detected
        self._running = False
        self._thread = None
        self._cap = None

        # Sub-modules (lazy loaded)
        self._face_encodings = []
        self._face_names = []
        self._yolo_model = None
        self._hands = None

        self._load_known_faces()

    def _load_known_faces(self):
        """Load known face encodings from memory."""
        if not self.memory:
            return
        try:
            import pickle
            faces = self.memory.get_known_faces()
            for f in faces:
                encoding = pickle.loads(f["encoding"])
                self._face_encodings.append(encoding)
                self._face_names.append(f["name"])
            logger.info(f"Loaded {len(self._face_names)} known faces")
        except Exception as e:
            logger.warning(f"Failed to load known faces: {e}")

    def start_camera(self):
        """Start background camera processing."""
        self._running = True
        self._thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._thread.start()
        logger.info("Vision system started")

    def stop_camera(self):
        """Stop camera."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._cap:
            self._cap.release()
        logger.info("Vision system stopped")

    def _camera_loop(self):
        """Main camera processing loop."""
        try:
            import cv2
            self._cap = cv2.VideoCapture(CAMERA_INDEX)
            if not self._cap.isOpened():
                logger.warning("Camera not available")
                return

            frame_delay = 1.0 / VISION_FPS
            last_face_check = 0
            face_check_interval = 2.0  # Check faces every 2 seconds

            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                now = time.time()
                # Face recognition every N seconds
                if now - last_face_check > face_check_interval:
                    self._process_faces(frame)
                    last_face_check = now

                time.sleep(frame_delay)

            self._cap.release()
        except ImportError:
            logger.warning("OpenCV not installed — vision disabled")
        except Exception as e:
            logger.error(f"Camera loop crashed: {e}")

    def _process_faces(self, frame):
        """Detect and recognize faces in a frame."""
        try:
            import face_recognition
            import cv2

            small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, locations)

            for encoding in encodings:
                if self._face_encodings:
                    matches = face_recognition.compare_faces(
                        self._face_encodings, encoding,
                        tolerance=FACE_RECOGNITION_TOLERANCE
                    )
                    if True in matches:
                        idx = matches.index(True)
                        name = self._face_names[idx]
                        if self.on_face_detected:
                            self.on_face_detected(name, known=True)
                    else:
                        if self.on_face_detected:
                            self.on_face_detected("Unknown", known=False)
                else:
                    if self.on_face_detected:
                        self.on_face_detected("Unknown", known=False)

        except ImportError:
            logger.debug("face_recognition not available")
        except Exception as e:
            logger.error(f"Face processing error: {e}")

    def register_face(self, name: str) -> str:
        """Capture and register a new face from webcam."""
        try:
            import cv2
            import face_recognition
            import pickle

            cap = cv2.VideoCapture(CAMERA_INDEX)
            if not cap.isOpened():
                return "Camera not available, Sir."

            ret, frame = cap.read()
            cap.release()
            if not ret:
                return "Failed to capture image, Sir."

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb)
            if not encodings:
                return "No face detected in frame, Sir. Please position yourself in front of the camera."

            encoding = encodings[0]
            self._face_encodings.append(encoding)
            self._face_names.append(name)

            if self.memory:
                self.memory.save_face(name, pickle.dumps(encoding))

            return f"Face registered for {name}, Sir. I'll recognize you from now on."

        except ImportError:
            return "face_recognition library not installed, Sir."
        except Exception as e:
            return f"Face registration failed, Sir: {str(e)}"

    def detect_objects(self, image=None) -> str:
        """Detect objects in an image or current camera frame using YOLOv8."""
        try:
            from ultralytics import YOLO
            import cv2

            if self._yolo_model is None:
                self._yolo_model = YOLO(YOLO_MODEL)
                logger.info("YOLOv8 model loaded")

            if image is None:
                cap = cv2.VideoCapture(CAMERA_INDEX)
                ret, image = cap.read()
                cap.release()
                if not ret:
                    return "Camera not available for object detection, Sir."

            results = self._yolo_model(image, verbose=False)
            detected = []
            for r in results:
                for box in r.boxes:
                    cls = r.names[int(box.cls)]
                    conf = float(box.conf)
                    if conf > 0.5:
                        detected.append(f"{cls} ({conf:.0%})")

            if detected:
                unique = list(set(detected))
                return f"Objects detected: {', '.join(unique)}"
            return "No objects detected, Sir."

        except ImportError:
            return "YOLOv8 (ultralytics) not installed, Sir."
        except Exception as e:
            return f"Object detection failed, Sir: {str(e)}"

    def analyze_screen(self) -> str:
        """Take screenshot and describe it (requires Gemini Vision API)."""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()

            from jarvis.config import GEMINI_API_KEY
            if not GEMINI_API_KEY:
                return "Screen analysis requires Gemini API key, Sir."

            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")

            response = model.generate_content([
                "Describe what's on this computer screen concisely.",
                screenshot
            ])
            return response.text

        except Exception as e:
            return f"Screen analysis failed, Sir: {str(e)}"

    def detect_gestures(self, frame=None) -> Optional[str]:
        """Detect hand gestures using MediaPipe."""
        try:
            import cv2
            import mediapipe as mp

            if self._hands is None:
                self._hands = mp.solutions.hands.Hands(
                    max_num_hands=1, min_detection_confidence=0.7
                )

            if frame is None:
                cap = cv2.VideoCapture(CAMERA_INDEX)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    return None

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._hands.process(rgb)

            if results.multi_hand_landmarks:
                landmarks = results.multi_hand_landmarks[0].landmark
                # Simple gesture detection
                thumb_tip = landmarks[4]
                index_tip = landmarks[8]
                wrist = landmarks[0]

                # Thumbs up: thumb tip above wrist, fingers curled
                if thumb_tip.y < wrist.y - 0.15:
                    return "thumbs_up"
                # Thumbs down: thumb tip below wrist
                if thumb_tip.y > wrist.y + 0.1:
                    return "thumbs_down"
                # Wave: hand open, fingers spread
                if all(landmarks[i].y < landmarks[i-2].y for i in [8, 12, 16, 20]):
                    return "wave"

            return None

        except ImportError:
            return None
        except Exception:
            return None

    def get_status(self) -> dict:
        return {
            "camera_active": self._running,
            "known_faces": len(self._face_names),
            "yolo_loaded": self._yolo_model is not None,
        }
