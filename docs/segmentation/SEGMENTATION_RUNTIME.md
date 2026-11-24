# Local semantic runtime

IMPLEMENTED: CPU ONNX Runtime from the existing optional model environment. No new neural framework or online inference dependency. Checkpoints are local, hash-verified, loaded once, and use explicit provider, tensor layout, RGB normalization and output signature. The model environment is installed using the existing `requirements-models.lock` instructions. Repository unit tests need no model download.

PIDNet: RGB /255, ImageNet mean/std; explicit 512x256 and 768x384 exports. Continuous logits resized in export before argmax. PP-LiteSeg Rockchip export: fixed RGB 512x512, /255 then (x-.5)/.5; 19-channel NCHW logits. No automatic model download, remote code, ensemble or silent fallback. A runtime inference error becomes recoverable unavailability; malformed contract outputs fail validation.

Offline replay executes configured semantic ticks synchronously. REALTIME uses one bounded worker and skips busy ticks, leaving the main pipeline free to advance. Native CPU work still competes for hardware; one intra-op thread is the default. This architecture is not a proven latency guarantee. Segmentation runs after other scheduled component calls. Source queues, metrics windows and mask buffers are bounded. No full logits history, per-frame model load, JVM startup or image export is added.

Session recording schema 5 stores compact summaries and region metadata, not dense masks/logits. Debug/review images are explicitly requested offline artifacts. Research exporters retain finite packets; this is not a runtime history.

Future priority: acquisition and fresh tracking/motion first, then detector, future risk, depth, semantics and optional debug. No production scheduler or deployment is introduced. Real-time rates must be measured, not inferred from source sampling cadence.
