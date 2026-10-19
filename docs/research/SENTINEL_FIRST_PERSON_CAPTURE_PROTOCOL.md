# First-person capture protocol

This is engineering data collection, not a safety trial. Use a normal walking
viewpoint close to the intended phone/wearable position. Keep a documented fixed
orientation and stable resolution. Retain original recordings where possible;
screen recordings introduce resampling, cropping and uncertain exposure timing.

Aim for about 12 clips of 45–120 seconds and 15–25 minutes overall, with normal
walking, natural turns/head or hand motion and stationary intervals. Include campus,
sidewalk, road edge, crossings, crowds, bicycles, motorcycles, moving and parked
vehicles, and safely available shaded/low-light scenes. These are coverage targets,
not grounds for inventing scene labels. One long video is supported with temporal
segments and guard bands; disclose its weaker independence.

Never stage dangerous encounters or deliberately enter traffic. Record approaching
and departing road users only as they occur naturally from a safe position.
Disable audio where possible. Store locally, do not upload or publish raw footage,
and exclude privacy-sensitive content from shared artifacts. No face identification
or license-plate recognition. Record ownership and permitted use honestly.

Sample by actual PTS at 2 Hz; the optional event-window exporter can add up to 5 Hz
around predeclared bicycle, motorcycle, crossing, vehicle, occlusion, turn or low-light
intervals. Freeze event windows before examining detector success/failure. Record the
policy and seed. Target 400–700 diverse reviewed frames for the current long clip;
actual coverage and P0 counts matter more than arbitrary totals.

Human review must add missed objects, remove false positives, correct classes and
boxes, and label lighting/motion/occlusion only when supported. Predictions are
DRAFT_MODEL_ASSISTED until a person reviews the entire frame. Never evaluate a
detector against its own unreviewed output. Keep calibration and qualification
sequences separate and preserve at least 60 seconds between different splits from
the same parent recording. Prefer genuinely different recordings in future versions.
