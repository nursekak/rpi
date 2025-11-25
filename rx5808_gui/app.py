"""PyQt6 GUI application for RX5808 control."""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QSizePolicy,
)

from .controller import Rx5808Controller
from .scanner import ChannelScanner, ChannelInfo
from .video import VideoWorker
from .config import channel_label, CHANNEL_FREQUENCIES


class VideoLabel(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #000;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def update_frame(self, image) -> None:
        pixmap = QPixmap.fromImage(image)
        self.setPixmap(
            pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class ChannelButton(QPushButton):
    def __init__(self, info: ChannelInfo, on_select) -> None:
        super().__init__(f"{info.label}\n{info.frequency} MHz")
        self.info = info
        self.on_select = on_select
        self.setCheckable(True)
        self.update_style()
        self.clicked.connect(self._handle_click)

    def update_style(self) -> None:
        if self.info.live:
            self.setStyleSheet("background-color: rgba(0, 180, 0, 160); color: white;")
        else:
            self.setStyleSheet("background-color: rgba(120, 0, 0, 120); color: white;")

    def _handle_click(self) -> None:
        self.on_select(self.info)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RX5808 Scanner")
        self.resize(1280, 720)

        self.controller = Rx5808Controller()
        self.video_worker: Optional[VideoWorker] = None

        self.channel_buttons: List[ChannelButton] = []
        self.scanner: Optional[ChannelScanner] = None

        self._init_ui()
        self._start_video()

    def _init_ui(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.channel_panel = QWidget()
        self.channel_panel.setFixedWidth(200)
        palette = self.channel_panel.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(20, 20, 20, 150))
        self.channel_panel.setAutoFillBackground(True)
        self.channel_panel.setPalette(palette)

        panel_layout = QVBoxLayout(self.channel_panel)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scan_status_label = QLabel("Scan status: Idle")
        self.scan_status_label.setStyleSheet("color: #bbb; font-size: 12px;")
        panel_layout.addWidget(self.scan_status_label)

        self.channel_scroll = QScrollArea()
        self.channel_scroll.setWidgetResizable(True)
        self.channel_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        scroll_content = QWidget()
        self.channel_list_layout = QVBoxLayout(scroll_content)
        self.channel_list_layout.addStretch()
        self.channel_scroll.setWidget(scroll_content)
        panel_layout.addWidget(self.channel_scroll)

        layout.addWidget(self.channel_panel)

        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)

        header = QHBoxLayout()
        header.addStretch()
        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self.toggle_scan)
        header.addWidget(self.scan_button)
        video_layout.addLayout(header)

        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        video_layout.addWidget(self.status_label)

        self.video_label = VideoLabel()
        video_layout.addWidget(self.video_label, stretch=1)

        layout.addWidget(video_container, stretch=1)
        self.setCentralWidget(central)

        self._populate_channel_buttons([])

    def _update_frame(self, image) -> None:
        self.video_label.update_frame(image)

    def toggle_scan(self) -> None:
        if self.scanner and self.scanner.is_alive():
            self.scanner.stop()
            self.scanner = None
            self.scan_button.setText("Start Scan")
            self.status_label.setText("Stopping scan...")
            self.scan_status_label.setText("Scan status: cancelling...")
            self._start_video()
            return

        self._stop_video()
        self.status_label.setText("Scan started")
        self.scan_status_label.setText("Scan status: starting...")
        self.scan_button.setText("Stop Scan")

        def on_progress(results: List[ChannelInfo], status: str) -> None:
            print(f"[App] Progress callback: {status}")
            def update() -> None:
                try:
                    print(f"[App] Updating UI with status: {status}")
                    self._populate_channel_buttons(results)
                    self.status_label.setText(status)
                    self.scan_status_label.setText(f"Scan status: {status}")
                    if status.startswith(("Completed", "Scan cancelled", "Scan error")):
                        self.scan_button.setText("Start Scan")
                        self.scanner = None
                        self.scan_status_label.setText("Scan status: Idle")
                        self._start_video()
                except Exception as e:
                    # Fallback if UI update fails
                    import traceback
                    print(f"[App] Error updating UI: {e}")
                    traceback.print_exc()
                    self.scan_status_label.setText(f"Scan status: Error - {e}")

            QTimer.singleShot(0, update)

        self.scanner = ChannelScanner(
            self.controller,
            on_progress=on_progress,
            min_signal_size=5000,
            auto_select=True,
        )
        self.scanner.start()
        
        # Verify thread started - if it doesn't update in 1 second, show error
        def check_thread():
            if self.scanner and self.scanner.is_alive():
                # Thread is running, it should have called on_progress by now
                pass
            else:
                # Thread died immediately
                self.scan_status_label.setText("Scan status: Thread failed to start")
                self.status_label.setText("Scan failed - check console for errors")
                self.scan_button.setText("Start Scan")
                self.scanner = None
                self._start_video()
        
        QTimer.singleShot(1000, check_thread)

    def _populate_channel_buttons(self, results: List[ChannelInfo]) -> None:
        while self.channel_list_layout.count() > 1:
            item = self.channel_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if not results:
            for idx, freq in enumerate(CHANNEL_FREQUENCIES):
                info = ChannelInfo(idx, channel_label(idx), freq, False, 0, 0.0)
                btn = ChannelButton(info, self._select_channel)
                self.channel_list_layout.insertWidget(self.channel_list_layout.count() - 1, btn)
            return

        # show strongest live channels first; fall back to all results if none live
        live_only = [info for info in results if info.live]
        display_list = live_only or results
        display_list.sort(key=lambda info: info.sample_size, reverse=True)

        for info in display_list:
            btn = ChannelButton(info, self._select_channel)
            self.channel_list_layout.insertWidget(self.channel_list_layout.count() - 1, btn)

    def _select_channel(self, info: ChannelInfo) -> None:
        self.controller.set_frequency(info.frequency)
        self.status_label.setText(f"Tuned to {info.frequency}MHz")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.scanner and self.scanner.is_alive():
            self.scanner.stop()
        self._stop_video()
        super().closeEvent(event)

    def _stop_video(self) -> None:
        if self.video_worker:
            self.video_worker.stop()
            self.video_worker = None

    def _start_video(self) -> None:
        if self.video_worker:
            return
        self.video_worker = VideoWorker()
        self.video_worker.frame_ready.connect(self._update_frame)
        self.video_worker.status_changed.connect(self.status_label.setText)
        self.video_worker.start()


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

