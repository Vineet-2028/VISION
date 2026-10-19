"""Explicit buffer operations paired with the Java core's exact coordinate mapping."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

import av
import numpy as np
from numpy.typing import NDArray

from .config import PreprocessConfig
from .contracts import Frame, PixelFormat
from .geometry import CoreGeometry, ImageMapping


@dataclass(frozen=True)
class ModelInputDescriptor:
    width: int
    height: int
    channels: int
    pixel_format: PixelFormat
    dtype: Literal["uint8", "float32"]
    layout: Literal["NHWC", "NCHW"]


@dataclass(frozen=True)
class PreparedImage:
    pixels: NDArray[np.uint8]
    descriptor: ModelInputDescriptor
    mapping: ImageMapping


class ImagePreprocessor(Protocol):
    def prepare(self, frame: Frame) -> PreparedImage: ...


class BasicPreprocessor:
    def __init__(self, geometry: CoreGeometry, config: PreprocessConfig) -> None:
        self.geometry, self.config = geometry, config
        source_width, source_height = geometry.source_width, geometry.source_height
        self.width = config.width or source_width
        self.height = config.height or source_height
        left, top = config.left, config.top
        self.resized = (self.width, self.height)
        if config.operation == "letterbox":
            scale = min(self.width / source_width, self.height / source_height)
            self.resized = (
                max(1, round(source_width * scale)),
                max(1, round(source_height * scale)),
            )
            left, top = (self.width - self.resized[0]) // 2, (self.height - self.resized[1]) // 2
        self.left, self.top = left, top
        self.mapping = geometry.mapping(
            config.operation, self.width, self.height, left, top, self.resized
        )

    def prepare(self, frame: Frame) -> PreparedImage:
        self.geometry.require_dimensions(frame.width, frame.height)
        pixels = frame.pixels
        config = self.config
        target_format = PixelFormat(config.pixel_format)
        if config.operation == "crop":
            pixels = pixels[self.top : self.top + self.height, self.left : self.left + self.width]
        resize = config.operation in {"resize", "letterbox"}
        if resize or frame.pixel_format != target_format:
            formats = {
                PixelFormat.RGB: "rgb24",
                PixelFormat.BGR: "bgr24",
                PixelFormat.GRAY: "gray",
                PixelFormat.RGBA: "rgba",
            }
            native = av.VideoFrame.from_ndarray(
                pixels[:, :, 0] if frame.pixel_format == PixelFormat.GRAY else pixels,
                format=formats[frame.pixel_format],
            )
            converted = native.reformat(
                width=self.resized[0] if resize else pixels.shape[1],
                height=self.resized[1] if resize else pixels.shape[0],
                format=formats[target_format],
            )
            pixels = cast(NDArray[np.uint8], converted.to_ndarray())
            if pixels.ndim == 2:
                pixels = pixels[:, :, None]
        if config.operation == "letterbox":
            padded = np.zeros((self.height, self.width, target_format.channels), dtype=np.uint8)
            padded[
                self.top : self.top + self.resized[1], self.left : self.left + self.resized[0]
            ] = pixels
            pixels = padded
        if config.layout == "NCHW":
            pixels = pixels.transpose(2, 0, 1)
        pixels.flags.writeable = False
        return PreparedImage(
            pixels,
            ModelInputDescriptor(
                self.width,
                self.height,
                target_format.channels,
                target_format,
                "uint8",
                config.layout,
            ),
            self.mapping,
        )
