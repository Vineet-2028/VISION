# Interaction evidence levels

IMPLEMENTED levels: IMAGE_GEOMETRIC (pixels), BEARING_GEOMETRIC (radians), WORLD_RESEARCH_UNVALIDATED (research meters). PHYSICAL_METRIC_VALIDATED is reserved; this analyzer never emits it. A physical-validity string alone cannot authorize promotion; future validated sensors require an explicit evidence authority and validation policy.

Quality is the worst applicable world/entity/trajectory/corridor/sample status, not an average confidence. GOOD, DEGRADED, UNRELIABLE and UNAVAILABLE are separate from physical validity. Long-horizon Task013 samples often make whole-forecast quality UNRELIABLE; individual samples retain their inherited quality. Predicted tracks degrade quality; stale track or trajectory sources suppress geometric forecasts. Reason codes and source ages survive recording.

UNVALIDATED: depth, ego translation, physical trajectory, semantics, user velocity, physical TTC/CPA and production safety. More correct mathematics cannot remove those limits. Software tests and synthetic references do not validate real physical measurements.
