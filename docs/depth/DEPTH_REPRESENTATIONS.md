# Depth representations

IMPLEMENTED: RELATIVE has unit NONE and explicit larger-is-nearer or larger-is-farther ordering. It has no optical-axis/ray-range interpretation; requesting meters raises an error. Relative scale may change between images and is not converted to meters.

METRIC has unit METERS and explicit CAMERA_Z or RAY_RANGE. The source label is MODEL_ESTIMATED_METRIC_DEPTH, never measured distance. Metric outputs must increase with distance; an inverse representation must be converted inside its provider.

DepthFrame contains identity, representation/range, immutable float32 map, immutable validity mask, optional quality map, exact Java image mapping, model/runtime provenance and processing times. Nonfinite, nonpositive metric and out-of-range values become invalid; stored zeros are masked and never substituted as distances. Quality is not a calibrated probability.

Each pixel uses continuous image-edge coordinates: array index i has center i+0.5. Default nearest samples floor(mapped_coordinate). Bilinear interpolation uses neighboring centers, requires every nonzero-weight neighbor valid, and never extrapolates.
