"""Low-level RX5808 GPIO controller."""

from __future__ import annotations

import os
import time

import RPi.GPIO as GPIO  # type: ignore

from .config import CHANNEL_VALUES, CHANNEL_FREQUENCIES, SPI_LOCK


class Rx5808Controller:
    def __init__(self, pin_ch1: int = 15, pin_ch2: int = 13, pin_ch3: int = 11) -> None:
        self.pin_data = pin_ch1
        self.pin_ss = pin_ch2
        self.pin_clock = pin_ch3

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_data, GPIO.OUT)
        GPIO.setup(self.pin_ss, GPIO.OUT)
        GPIO.setup(self.pin_clock, GPIO.OUT)

    # ---------------------------------------------------------------- helpers
    def _spi_sendbit_1(self) -> None:
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_data, GPIO.HIGH)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.HIGH)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)

    def _spi_sendbit_0(self) -> None:
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_data, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.HIGH)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)

    def _spi_readbit(self) -> bool:
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.HIGH)
        time.sleep(1e-6)
        res = GPIO.input(self.pin_data) == GPIO.HIGH
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        return res

    def _spi_select_low(self) -> None:
        time.sleep(1e-6)
        GPIO.output(self.pin_ss, GPIO.LOW)
        time.sleep(1e-6)

    def _spi_select_high(self) -> None:
        time.sleep(1e-6)
        GPIO.output(self.pin_ss, GPIO.HIGH)
        time.sleep(1e-6)

    # --------------------------------------------------------------- registers
    def _get_register(self, reg: int) -> int:
        self._spi_select_high()
        time.sleep(1e-6)
        self._spi_select_low()

        for i in range(4):
            if reg & (1 << i):
                self._spi_sendbit_1()
            else:
                self._spi_sendbit_0()

        self._spi_sendbit_0()
        GPIO.setup(self.pin_data, GPIO.IN)

        data = 0
        for i in range(20):
            if self._spi_readbit():
                data |= (1 << i)

        self._spi_select_high()
        time.sleep(1e-6)
        GPIO.setup(self.pin_data, GPIO.OUT)

        GPIO.output(self.pin_ss, GPIO.LOW)
        GPIO.output(self.pin_clock, GPIO.LOW)
        GPIO.output(self.pin_data, GPIO.LOW)
        return data

    def _set_register(self, reg: int, value: int) -> None:
        self._spi_select_high()
        time.sleep(1e-6)
        self._spi_select_low()

        for i in range(4):
            if reg & (1 << i):
                self._spi_sendbit_1()
            else:
                self._spi_sendbit_0()

        self._spi_sendbit_1()
        for _ in range(20):
            if value & 0x1:
                self._spi_sendbit_1()
            else:
                self._spi_sendbit_0()
            value >>= 1

        self._spi_select_high()
        time.sleep(1e-6)
        self._spi_select_low()

    # ---------------------------------------------------------------- public
    def current_frequency(self) -> str:
        with SPI_LOCK:
            val = self._get_register(0x01)

        for idx, data in enumerate(CHANNEL_VALUES):
            if data == val:
                return f"{CHANNEL_FREQUENCIES[idx]}MHz"
        return f"Unknown ({hex(val)})"

    def set_frequency(self, freq_mhz: int | str) -> str:
        freq_str = str(freq_mhz).replace("MHz", "")
        target = None
        for idx, freq in enumerate(CHANNEL_FREQUENCIES):
            if str(freq) == freq_str:
                target = CHANNEL_VALUES[idx]
                break

        if target is None:
            raise ValueError(f"Unknown frequency {freq_mhz}")

        with SPI_LOCK:
            self._set_register(0x08, 0x03F40)
            self._set_register(0x01, target)
            GPIO.output(self.pin_ss, GPIO.LOW)
            GPIO.output(self.pin_clock, GPIO.LOW)
            GPIO.output(self.pin_data, GPIO.LOW)

        return freq_str

    @staticmethod
    def ensure_device(video_device: str) -> str:
        if os.path.exists(video_device):
            return video_device

        for candidate in sorted(
            os.path.join("/dev", f) for f in os.listdir("/dev") if f.startswith("video")
        ):
            return candidate

        raise FileNotFoundError("No /dev/video* device found")
"""Low-level RX5808 GPIO controller."""

from __future__ import annotations

import os
import time
from typing import Optional

import RPi.GPIO as GPIO  # type: ignore

from .config import CHANNEL_VALUES, CHANNEL_FREQUENCIES, SPI_LOCK


class Rx5808Controller:
    """Wrapper around RX5808 SPI bit-banging."""

    def __init__(
        self,
        pin_ch1: int = 15,
        pin_ch2: int = 13,
        pin_ch3: int = 11,
    ) -> None:
        self.pin_data = pin_ch1
        self.pin_ss = pin_ch2
        self.pin_clock = pin_ch3

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_data, GPIO.OUT)
        GPIO.setup(self.pin_ss, GPIO.OUT)
        GPIO.setup(self.pin_clock, GPIO.OUT)

    # ------------------------------------------------------------------ helpers
    def _spi_sendbit_1(self) -> None:
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_data, GPIO.HIGH)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.HIGH)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)

    def _spi_sendbit_0(self) -> None:
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_data, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.HIGH)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)

    def _spi_readbit(self) -> bool:
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        GPIO.output(self.pin_clock, GPIO.HIGH)
        time.sleep(1e-6)
        result = GPIO.input(self.pin_data) == GPIO.HIGH
        GPIO.output(self.pin_clock, GPIO.LOW)
        time.sleep(1e-6)
        return result

    def _spi_select_low(self) -> None:
        time.sleep(1e-6)
        GPIO.output(self.pin_ss, GPIO.LOW)
        time.sleep(1e-6)

    def _spi_select_high(self) -> None:
        time.sleep(1e-6)
        GPIO.output(self.pin_ss, GPIO.HIGH)
        time.sleep(1e-6)

    # ---------------------------------------------------------------- registers
    def _get_register(self, reg: int) -> int:
        self._spi_select_high()
        time.sleep(1e-6)
        self._spi_select_low()

        for i in range(4):
            if reg & (1 << i):
                self._spi_sendbit_1()
            else:
                self._spi_sendbit_0()

        self._spi_sendbit_0()
        GPIO.setup(self.pin_data, GPIO.IN)

        data = 0
        for i in range(20):
            if self._spi_readbit():
                data |= (1 << i)

        self._spi_select_high()
        time.sleep(1e-6)
        GPIO.setup(self.pin_data, GPIO.OUT)

        GPIO.output(self.pin_ss, GPIO.LOW)
        GPIO.output(self.pin_clock, GPIO.LOW)
        GPIO.output(self.pin_data, GPIO.LOW)
        return data

    def _set_register(self, reg: int, value: int) -> None:
        self._spi_select_high()
        time.sleep(1e-6)
        self._spi_select_low()

        for i in range(4):
            if reg & (1 << i):
                self._spi_sendbit_1()
            else:
                self._spi_sendbit_0()

        self._spi_sendbit_1()
        for _ in range(20):
            if value & 0x1:
                self._spi_sendbit_1()
            else:
                self._spi_sendbit_0()
            value >>= 1

        self._spi_select_high()
        time.sleep(1e-6)
        self._spi_select_low()

    # ----------------------------------------------------------------- public
    def current_frequency(self) -> str:
        with SPI_LOCK:
            data = self._get_register(0x01)

        for index, value in enumerate(CHANNEL_VALUES):
            if value == data:
                return f"{CHANNEL_FREQUENCIES[index]}MHz"
        return f"Unknown ({hex(data)})"

    def set_frequency(self, freq_mhz: int | str) -> str:
        freq_str = str(freq_mhz).replace("MHz", "")
        target = None
        for idx, freq in enumerate(CHANNEL_FREQUENCIES):
            if str(freq) == freq_str:
                target = CHANNEL_VALUES[idx]
                break

        if target is None:
            raise ValueError(f"Unknown frequency: {freq_mhz}")

        with SPI_LOCK:
            print(f"Selecting frequency {freq_str}MHz ({hex(target)})")
            self._set_register(0x08, 0x03F40)
            self._set_register(0x01, target)
            GPIO.output(self.pin_ss, GPIO.LOW)
            GPIO.output(self.pin_clock, GPIO.LOW)
            GPIO.output(self.pin_data, GPIO.LOW)

        return freq_str

    # -------------------------------------------------------------- utilities
    @staticmethod
    def ensure_device(video_device: str) -> str:
        if os.path.exists(video_device):
            return video_device

        # auto-detect /dev/video*
        for candidate in sorted(
            (os.path.join("/dev", f) for f in os.listdir("/dev") if f.startswith("video"))
        ):
            return candidate  # first match

        raise FileNotFoundError("No /dev/video* device found")

