"""Explicit isolated ONNX runtime loading for local rescue experiments only."""

import ctypes
import os
import sys
from pathlib import Path

_preloaded_libraries = {}


def activate_onnx(runtime, libraries, cudnn_directory=None):
    runtime, libraries = runtime.resolve(), libraries.resolve()
    if not (runtime / "onnxruntime/__init__.py").is_file():
        raise ValueError("Isolated ONNX runtime directory is missing")
    sys.path.insert(0, str(runtime))
    sys.path.append(str(libraries))
    import onnxruntime as ort

    if not Path(ort.__file__).resolve().is_relative_to(runtime):
        raise RuntimeError("A different ONNX runtime was already imported")
    paths = [
        path
        for path in (libraries / "nvidia").glob("*/bin")
        if cudnn_directory is None or path.parent.name != "cudnn"
    ]
    if cudnn_directory is not None:
        paths.append(cudnn_directory.resolve())
    directories = []
    try:
        for path in paths:
            directories.append(os.add_dll_directory(str(path)))
        # cuDNN's legacy dynamic loader may not use AddDllDirectory when resolving
        # NVRTC by basename. Load the existing isolated DLL explicitly first.
        nvrtc = libraries / "nvidia/cuda_nvrtc/bin/nvrtc64_120_0.dll"
        if nvrtc.is_file() and str(nvrtc) not in _preloaded_libraries:
            _preloaded_libraries[str(nvrtc)] = ctypes.WinDLL(str(nvrtc))
        ort.preload_dlls(cudnn=cudnn_directory is None)
        if cudnn_directory is not None:
            ort.preload_dlls(cuda=False, cudnn=True, directory=str(cudnn_directory.resolve()))
        return ort, directories
    except BaseException:
        for directory in directories:
            directory.close()
        raise
