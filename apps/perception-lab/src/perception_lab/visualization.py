"""Optional Tk adapter; no GUI imports or display connections in headless mode."""

from typing import Protocol

from .contracts import Cancellation, Frame, FrameResult, LabError, PixelFormat
from .overlays import FrameInfoOverlay


class Renderer(Protocol):
    def render(
        self,
        frame: Frame,
        result: FrameResult,
        source_fps: float | None,
        processing_fps: float | None,
    ) -> None: ...
    def close(self) -> None: ...


class TkRenderer:
    def __init__(self, cancel: Cancellation, mode: str, calibration_status: str) -> None:
        import tkinter as tk

        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Sentinel Perception Laboratory — experimental observations")
        self.root.protocol("WM_DELETE_WINDOW", cancel.cancel)
        self.label = tk.Label(self.root)
        self.label.pack()
        self.info = tk.Label(self.root, justify="left")
        self.info.pack()
        self.photo: tk.PhotoImage | None = None
        self.mode, self.calibration_status = mode, calibration_status
        self.overlay = FrameInfoOverlay()

    def render(
        self,
        frame: Frame,
        result: FrameResult,
        source_fps: float | None,
        processing_fps: float | None,
    ) -> None:
        if frame.pixel_format != PixelFormat.RGB:
            raise LabError("RENDER_REQUIRES_RGB")
        ppm = f"P6\n{frame.width} {frame.height}\n255\n".encode() + frame.pixels.tobytes()
        self.photo = self.tk.PhotoImage(data=ppm, format="PPM")
        self.label.configure(image=self.photo)
        self.info.configure(
            text="\n".join(
                self.overlay.lines(
                    result, self.mode, self.calibration_status, source_fps, processing_fps
                )
            )
        )
        self.root.update_idletasks()
        self.root.update()

    def close(self) -> None:
        self.photo = None
        self.root.destroy()
