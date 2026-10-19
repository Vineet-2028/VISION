# Depth architecture

Status: IMPLEMENTED and evaluated for local prototype/research; physical accuracy remains UNVALIDATED. Task009 is not implemented.

Frame -> independent DepthAdapter -> DepthFrame -> region DepthEstimate -> optional detection/track association. Components return Sentinel values, never vendor tensors. DepthOutput is now an alias of DepthFrame; the old string-only placeholder was removed. Detector and tracker contracts are unchanged.

The lab owns runtime selection, scheduling and memory. Guardian Java owns image transforms, calibrated rays and spatial transform composition. Depth maps remain at native output resolution. One immutable ownership copy prevents caller aliases from changing observations; sampling never copies a full map per object. Affine sampling uses a Java-evaluated basis in the geometry boundary.

FrameResult can contain current depth and compact detection/track samples. Default recorder serializes only the depth summary, never dense arrays or Java objects. No prior map or per-track depth history is retained. Recorded sessions remain opt-in; JSONL disk usage grows with session duration and requires an external retention policy.

Task011 may consume TrackSnapshot plus TrackDepthObservation without provider internals. Task009 may consume DepthFrame and calibrated rays while supplying exact-time pose later. No optical flow, ego-motion, world model, physical object velocity, TTC or risk is implemented here.
