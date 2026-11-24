# Guardian fast path

The single pipeline owner executes detector, tracker, WorldState, corridor,
trajectory, interaction, risk, attention and alert. Optional depth, optical flow
and segmentation/surface extraction execute outside that chain. A missing or
rejected result uses existing unavailable/degraded/image-space semantics.

Pending jobs are replaced with the newest eligible source frame. Returned evidence
retains its original frame, source, timestamp and quality. Future/wrong-source
evidence fails validation. Evidence older than its configured validity budget is
rejected. No alert expiry or quality threshold is increased.

Acceptance requires the full ten-minute run and regression gates; a successful
short pilot does not establish engineering demo readiness. Human usefulness,
physical accuracy and production safety remain unvalidated.
