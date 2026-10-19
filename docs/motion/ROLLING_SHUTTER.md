# Rolling shutter timing

## IMPLEMENTED

RollingShutterModel explicitly represents UNKNOWN, GLOBAL_SHUTTER and
ROLLING_SHUTTER. It operates on the original physical sensor IMAGE identity and
continuous row-center coordinates y in [0.5,H-0.5].

Its supplied timestamp is the **first scanned row's exposure midpoint**. readoutSpanNanos
means first-to-last row midpoint separation, not per-row exposure duration or delivery
latency. For top-to-bottom scan:

    fraction = (y-0.5)/(H-1)
    row_time = first_row_midpoint + round(fraction*readout_span)

Bottom-to-top replaces fraction with 1-fraction. Global shutter returns the same
midpoint for every row; UNKNOWN returns unavailable. Single-row images require
zero span. Total end timestamp is checked for overflow. Fractional rows support
continuous geometry. Final integer rounding contributes up to half a nanosecond;
floating-point fraction/product arithmetic adds further error, especially for
unrealistically large readout spans. Large absolute session timestamps stay in
integer arithmetic, so they do not themselves reduce row-offset precision.

frameMidpoint gives first_row_midpoint+floor(span/2), matching Task 003's exposure-
midpoint convention to integer precision. A timestamp from a camera driver may mean
exposure START, so the adapter must convert using the actual exposure duration before
constructing this model. Do not merely relabel start as midpoint.

Map cropped/rotated/model coordinates back to physical sensor coordinates before
row lookup. A display row after a 90-degree rotation is not a sensor scan row.
Row timing does not correct rolling-shutter motion by itself; pose history at row
time is necessary for any later correction.

## PLANNED / RESEARCH

Measure actual scan direction, readout span and camera timestamp semantics per mode.
Do not assume a phone's metadata is accurate without testing. Full rolling-shutter
image correction, row-dependent motion uncertainty and exposure integration are
deferred. RND-IMU-011 records the characterization plan.
