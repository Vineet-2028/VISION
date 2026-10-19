# ADR 0004: bounded Python and Java desktop laboratory

Accepted for Task 005. Python 3.12+ owns desktop media, arrays, scheduling and
experiment artifacts. Java guardian-core remains the sole geometry/physics
implementation. JPype loads its built JAR once per process. No Java library imports
Python, FFmpeg, Spring, Android or an ML runtime.

Python alone offers the strongest model bake-off, ONNX, profiling and array ecosystem
but translating the existing mathematics would create a second authority. Java alone
has direct core access and Android parity, but makes rapid Python-model experiments
and decoder integration harder. A subprocess RPC server would add protocol framing,
process lifecycle and serialization costs. The selected JNI bridge is bounded to
`geometry.py`; native/dynamic types do not escape its typed wrapper. Build the JAR
before replay. A matching 64-bit JVM is a deliberate desktop prerequisite, not an
Android runtime dependency. JVM class resolution and transforms are initialized
outside the frame loop. No notebook is production code.

PyAV is selected over OpenCV because frame PTS and rational time bases are explicit.
The installed version is locked, including its FFmpeg wheel dependency. See
[PyAV time semantics](https://pyav.org/docs/stable/api/time.html) and
[JPype integration](https://jpype.readthedocs.io/en/latest/userguide.html).
PyAV's published documentation version can lag wheel releases; generated VFR fixtures
test our installed behavior instead of inferring it from an average FPS field.

PyAV is BSD-licensed; FFmpeg and included codecs have separate LGPL/GPL obligations
depending on the wheel/build configuration. Review the actual redistributed binary
and codec/patent obligations before shipping installers; this repository does not
redistribute codec binaries. See [FFmpeg licensing](https://ffmpeg.org/legal.html).
No model runtime, GPU framework, HTTP framework, notebook server or telemetry SDK is
needed. Pydantic provides strict finite schema validation; NumPy owns pixel buffers.

The lab is local experimental infrastructure. Realtime replay is cooperative and
bounded; it is not a hard realtime camera loop or a validated assistive device.
Live cameras, production model choices and mobile acceleration remain future work.
