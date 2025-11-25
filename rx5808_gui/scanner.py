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

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        results: List[ChannelInfo] = []
        first_live = None
        total = len(CHANNEL_FREQUENCIES)

        try:
            # Immediate progress update to confirm thread started
            print(f"[Scanner] Thread started, total channels: {total}")
            self.on_progress(results, f"Scanning (0/{total}) - Starting...")
            
            # Small delay to ensure UI updates
            time.sleep(0.05)
            print(f"[Scanner] Starting channel loop...")
            
            for idx, freq in enumerate(CHANNEL_FREQUENCIES):
                if self._stop_event.is_set():
                    self.on_progress(results, "Scan cancelled")
                    return

                label = channel_label(idx)
                self.on_progress(results, f"Scanning ({idx + 1}/{total}) - Testing {label} ({freq}MHz)")
                
                info = self._probe(idx, freq)
                results.append(info)
                
                status = f"Scanning ({idx + 1}/{total}) - {label} ({freq}MHz): {'LIVE' if info.live else 'no signal'}"
                self.on_progress(results, status)

                if info.live and first_live is None and self.auto_select:
                    first_live = freq

            if first_live is not None:
                self.controller.set_frequency(first_live)
                self.on_progress(results, f"Completed. Best channel: {first_live}MHz")
            else:
                self.on_progress(results, "Completed. No live signals")
        except Exception as exc:  # keep UI responsive on hardware errors
            import traceback
            error_msg = f"Scan error: {exc}"
            print(f"[Scanner] Exception: {error_msg}")
            traceback.print_exc()
            self.on_progress(results, error_msg)

    # ----------------------------------------------------------------- helpers
    def _probe(self, idx: int, freq: int) -> ChannelInfo:
        if self._stop_event.is_set():
            # Return dummy info if stopped
            return ChannelInfo(
                index=idx,
                label=channel_label(idx),
                frequency=freq,
                live=False,
                sample_size=0,
            )
        
        try:
            self.controller.set_frequency(freq)
        except Exception as e:
            # If controller fails, return error info
            return ChannelInfo(
                index=idx,
                label=channel_label(idx),
                frequency=freq,
                live=False,
                sample_size=0,
            )
        
        # Check stop event during sleep
        for _ in range(20):  # 0.2s = 20 * 0.01s
            if self._stop_event.is_set():
                return ChannelInfo(
                    index=idx,
                    label=channel_label(idx),
                    frequency=freq,
                    live=False,
                    sample_size=0,
                )
            time.sleep(0.01)

        if self._stop_event.is_set():
            return ChannelInfo(
                index=idx,
                label=channel_label(idx),
                frequency=freq,
                live=False,
                sample_size=0,
            )

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
        proc = None
        try:
            # Start process and check for stop during execution
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Wait with periodic stop checks
            elapsed = 0
            while proc.poll() is None and elapsed < 4:
                if self._stop_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break
                time.sleep(0.1)
                elapsed += 0.1
            
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
            elif proc.returncode == 0 and os.path.exists(tmp_path):
                size = os.path.getsize(tmp_path)
        except Exception:
            size = 0
        finally:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.5)
                except:
                    proc.kill()
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

        live = size >= self.min_signal_size
        return ChannelInfo(
            index=idx,
            label=channel_label(idx),
            frequency=freq,
            live=live,
            sample_size=size,
        )
