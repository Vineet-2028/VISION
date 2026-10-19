# Time synchronization

## IMPLEMENTED

Task 004's pre-task audit confirmed Task 002/003 conventions before implementation:
nonnegative elapsed nanoseconds plus clock/session identity; subtraction before
conversion to seconds; finite SI values; Hamilton quaternion order; DEVICE->WORLD
poses; raw specific force distinct from linear acceleration; Java 8 compatibility.
Existing math and camera geometry have not been rewritten.

Temporal.durationSeconds(start,end) requires end>=start and a common clock. Zero
duration is valid for timing, not differentiation. Nonnegative long subtraction
cannot overflow; midpoint uses start+(end-start)/2. ClockMapping explicitly applies
a signed constant offset with checked addition and unavailable results for negative
or overflowed target time. It never discovers synchronization or modifies timestamps
because delivery was late. No algorithm reads a system clock.

TimedObservation lets immutable existing observations enter SampleBuffer without
duplicate timestamp wrappers. TimedVectorEstimate binds the existing VectorEstimate
quantity, validity, confidence and optional deviations to measurement time.
Unknown values stay absent, never zero measurements.

SampleBuffer is single-owner, not thread-safe. Capacity and retention are bounded;
late acceptance is explicitly configurable. Insertions report ACCEPTED,
ACCEPT_AND_REORDER, DUPLICATE, REJECT_TOO_LATE or OUTSIDE_BUFFER. Duplicates are
rejected (first observation wins). The watermark is the newest retained measurement,
not wall-clock now. Oldest samples are evicted deterministically. Lookups are inclusive
before/after, nearest ties prefer earlier. Snapshots copy the list; immutable sample
objects may be shared. Reset clears data and clock binding.

PoseHistory enforces fixed device/world identities and supports temporal lookup.
SensorSynchronizer owns pose, orientation, DEVICE gyro and WORLD linear-acceleration
buffers. It does not manufacture translation from orientation or compensate raw
acceleration without an aligned orientation. Ingestion and lookup must share one
owner; publish immutable results to other threads.
One clock identity is bound across all streams on first accepted ingestion;
incompatible clock input is rejected before changing any buffer. Reset clears
the binding. Constant-offset mapping must happen explicitly before ingestion.

Lookup modes are EXACT, INTERPOLATED, NEAREST_ALLOWED and UNAVAILABLE. Consumer
policy supplies maximum interpolation span, nearest age and whether future nearest
is permitted. Invalid observations are barriers, not silently skipped.
NEAREST_ALLOWED retains its actual measurement time. It cannot be passed to Task 003
as an exact capture-time pose without failing its time check. Source observations
remain available for uncertainty and age inspection. Temporal.age distinguishes
FRESH, STALE, FUTURE and INVALID; wrong clocks throw.
Alignment exposes signed source ages relative to requested time; negative ages
identify future interpolation endpoints or explicitly permitted future nearest data.

Scalar/vector interpolation uses (1-alpha)*x0+alpha*x1 with alpha computed from integer
nanosecond differences. Only closed intervals are accepted, no extrapolation; zero
span is unavailable. Pose translation uses linear interpolation, rotation uses SLERP.
Exact endpoints retain original uncertainty. Interior estimates conservatively cap
confidence by the lesser input score and leave derived deviations unknown rather
than invent covariance. Alignment quality describes availability/timing, not safety.

ProcessingTiming separates capture, delivery, processing start and end on one mapped
clock and enforces their ordering. Capture remains the reference for scene state.
TimingMetrics provides mean/std/min/max intervals and configured gap ratios. A long
gap is evidence of a gap, not proof of a particular number of dropped samples.
The future owner can count insertion statuses for out-of-order, duplicate and rejected
measurements; no global counters or telemetry system are installed. Bias availability
is explicit in each bias estimate's optional value. Known gyro/linear-acceleration
sample contracts do not encode invalid markers: an adapter detecting an invalid
sensor epoch must reset the affected synchronization lifecycle, not insert zero data.

## PLANNED / RESEARCH

Adapters must measure camera/sensor clock relationships and exposure semantics.
A future affine mapping is t_target=a*t_source+b; rate ratio, offset, fit uncertainty
and validity interval need evidence before implementation. AOSP discusses sensor
timestamp jitter/drift and camera timestamp timebase metadata:
[sensor HAL](https://source.android.com/docs/core/interaction/sensors/hal-interface),
[camera metadata](https://android.googlesource.com/platform/system/media/+/c61e164fe52ee63bc3d9be8a6207e9a6719a9c1c/camera/docs/metadata_properties.xml).
These references do not prove synchronization accuracy on a target device.
