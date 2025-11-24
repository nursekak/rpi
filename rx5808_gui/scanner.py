"""Channel scanning logic."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, List

import subprocess

from .config import (
    CHANNEL_FREQUENCIES,
    channel_label,
    VIDEO_DEVICE,
    VIDEO_FORMAT,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
)
from .controller import Rx5808Controller


@dataclass
class ChannelInfo:
    index: int
    label: str
    frequency: int
    live: bool
    sample_size: int


class ChannelScanner(threading.Thread):
    """Background worker that probes every channel."""

    def __init__(
        self,
        controller: Rx5808Controller,
        *,
        on_progress: Callable[[List[ChannelInfo], str], None],
        min_signal_size: int = 5000,
        auto_select: bool = True,
    ) -> None:
        super().__init__(daemon=True)
        self.controller = controller
        self.on_progress = on_progress
        self.min_signal_size = min_signal_size
        self.auto_select = auto_select
        self._stop_event = threading.Event()
        self.results: List[ChannelInfo] = []
        self.status: str = "Idle"

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        self.results.clear()
        first_live = None

        for idx, freq in enumerate(CHANNEL_FREQUENCIES):
            if self._stop_event.is_set():
                self.status = "Scan cancelled"
                self.on_progress(self.results, self.status)
                return

            info = self._probe(idx, freq)
            self.results.append(info)
            self.status = f"Scanning ({idx + 1}/{len(CHANNEL_FREQUENCIES)})"
            self.on_progress(self.results, self.status)

            if info.live and first_live is None and self.auto_select:
                first_live = freq

        if first_live is not None:
            self.controller.set_frequency(first_live)
            self.status = f"Completed. Best channel: {first_live}MHz"
        else:
            self.status = "Completed. No live signals"

        self.on_progress(self.results, self.status)

    # ----------------------------------------------------------------- helpers
    def _probe(self, idx: int, freq: int) -> ChannelInfo:
        self.controller.set_frequency(freq)
        time.sleep(0.2)

        # capture single JPEG using gstreamer
        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

        cmd = (
            "gst-launch-1.0 -q "
            f"v4l2src device={VIDEO_DEVICE} num-buffers=1 "
            f"! video/x-raw, format={VIDEO_FORMAT}, framerate={VIDEO_FPS}/1, "
            f"width={VIDEO_WIDTH}, height={VIDEO_HEIGHT} "
            "! jpegenc "
            f"! filesink location={tmp_path}"
        )

        size = 0
        try:
            subprocess.run(cmd, shell=True, timeout=4, check=True)
            if os.path.exists(tmp_path):
                size = os.path.getsize(tmp_path)
        except subprocess.SubprocessError:
            size = 0
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        live = size >= self.min_signal_size
        return ChannelInfo(
            index=idx,
            label=channel_label(idx),
            frequency=freq,
            live=live,
            sample_size=size,
        )

