"""Video capture worker using OpenCV."""

from __future__ import annotations

import cv2  # type: ignore
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from .config import VIDEO_DEVICE, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS


class VideoWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(str)

    def __init__(self, device: str = VIDEO_DEVICE) -> None:
        super().__init__()
        self.device = device

    def stop(self) -> None:
        self.requestInterruption()
        self.wait(1000)

    def run(self) -> None:  # noqa: D401
        cap = cv2.VideoCapture(self.device)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, VIDEO_FPS)

        if not cap.isOpened():
            self.status_changed.emit("Unable to open video device")
            return

        self.status_changed.emit("Video started")
        while not self.isInterruptionRequested():
            ret, frame = cap.read()
            if not ret:
                self.status_changed.emit("Video read error")
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(
                rgb.data,
                rgb.shape[1],
                rgb.shape[0],
                rgb.strides[0],
                QImage.Format.Format_RGB888,
            )
            self.frame_ready.emit(image.copy())

        cap.release()
        self.status_changed.emit("Video stopped")
