from setuptools import setup, find_packages

setup(
    name="rx5808-gui",
    version="0.1.0",
    description="PyQt6 GUI for RX5808 video scanner",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4",
        "opencv-python>=4.5",
        "RPi.GPIO>=0.7",
    ],
    entry_points={
        "console_scripts": [
            "rx5808-gui=rx5808_gui.app:run",
        ]
    },
)
from setuptools import setup, find_packages

setup(
    name="rx5808-gui",
    version="0.1.0",
    description="PyQt6 GUI for RX5808 video scanner",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4",
        "opencv-python>=4.5",
        "RPi.GPIO>=0.7",
    ],
    entry_points={
        "console_scripts": [
            "rx5808-gui=rx5808_gui.app:run",
        ]
    },
)

