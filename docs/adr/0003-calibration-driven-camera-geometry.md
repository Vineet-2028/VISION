# ADR 0003: Camera geometry is calibration-driven

Status: Accepted for Task 003, 2026-10-13.

Normalized detector coordinates are image fractions, not physical directions.
Resolution changes, crop, rotation and distortion can change their interpretation.
All future spatial reasoning must pass through calibrated camera geometry when
calibration is available. Restore model coordinates to the calibrated image first.

Extend guardian-core, preserving Java 8 and zero runtime dependencies. Immutable
calibration identities bind observations to dimensions and frame identities.
Camera/device/world transforms and timestamps are explicit; no hardware mapping is
assumed. Bounded inverse distortion fails explicitly. Ground intersections are
nominal candidates, not measured object locations or steering instructions.

A degraded approximate camera model may be introduced only by an explicit future
policy: mark DEGRADED, increase represented uncertainty, avoid false metric precision
and prohibit unsafe steering guidance. No automatic fallback is implemented here.
Unknown quality does not mean zero error; availability of math is not safety validity.

Horizon curves, covariance propagation and calibration serialization adapters remain
documented future work. A general CV/matrix framework and a second geometry module
would add boundaries without a present consumer, so neither is introduced.
