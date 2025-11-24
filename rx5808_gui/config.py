"""Application configuration and shared constants."""

from threading import Lock

# Video defaults
VIDEO_DEVICE = "/dev/video0"
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_FORMAT = "YUY2"

# Output frame rate for GUI refresh (ms)
GUI_FRAME_INTERVAL_MS = 50

# Channel definitions (same order as RX5808 lookup tables)
CHANNEL_VALUES = [
    # Channel 1 - 8
    0x281D, 0x288F, 0x2902, 0x2914, 0x2987, 0x2999, 0x2A0C, 0x2A1E,  # Raceband
    0x2A05, 0x299B, 0x2991, 0x2987, 0x291D, 0x2913, 0x2909, 0x289F,  # Band A
    0x2903, 0x290C, 0x2916, 0x291F, 0x2989, 0x2992, 0x299C, 0x2A05,  # Band B
    0x2895, 0x288B, 0x2881, 0x2817, 0x2A0F, 0x2A19, 0x2A83, 0x2A8D,  # Band E
    0x2906, 0x2910, 0x291A, 0x2984, 0x298E, 0x2998, 0x2A02, 0x2A0C,  # Band F / Airwave
    0x2609, 0x261C, 0x268E, 0x2701, 0x2713, 0x2786, 0x2798, 0x280B,  # Band D / 5.3
]

CHANNEL_FREQUENCIES = [
    # Channel 1 - 8
    5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917,  # Raceband
    5865, 5845, 5825, 5805, 5785, 5765, 5745, 5725,  # Band A
    5733, 5752, 5771, 5790, 5809, 5828, 5847, 5866,  # Band B
    5705, 5685, 5665, 5645, 5885, 5905, 5925, 5945,  # Band E
    5740, 5760, 5780, 5800, 5820, 5840, 5860, 5880,  # Band F / Airwave
    5362, 5399, 5436, 5473, 5510, 5547, 5584, 5621,  # Band D / 5.3
]

def channel_label(index: int) -> str:
    """Return default display name for a frequency channel."""
    return f"FPV {index + 1}"

# Shared locks
SPI_LOCK = Lock()

