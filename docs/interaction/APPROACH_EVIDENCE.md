# Approach evidence

IMPLEMENTED: distance to the frozen corridor at origin versus final supplied sample yields APPROACHING, RECEDING or STATIONARY_OR_LATERAL using explicit domain tolerances. A path that gets closer and then returns can be INDETERMINATE. This is geometric endpoint evidence, not physical range closing. All intermediate distances remain available to future consumers.

Bearing hypotheses compare absolute horizontal angle to CAMERA_FORWARD_BEARING_NOT_RANGE, provided calibration identity matches. This is a camera-axis reference, not a promise that the user's body heading or corridor centerline matches it. Metric radial closing speed is available only through the Guardian research relative-motion adapter. Positive means closing, negative means receding.

Left/right direction uses signed lateral/image displacement. World ground-plane forward coordinates may label AHEAD/BEHIND; image pixels never imply behind the user. Static entities inside remain present even with unavailable/non-closing TTC. No category-specific speed, dangerousness, alert, cooldown or attention policy is introduced.
