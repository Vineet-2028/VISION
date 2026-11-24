# Entity-corridor relations

IMPLEMENTED immutable relations retain WorldEntityId, source timestamp, INSIDE / INTERSECTS / NEAR_BOUNDARY / OUTSIDE / UNKNOWN, basis, representative source, source evidence, quality and assumptions. All bounded input entities receive one relation in input order. No outside object is deleted or permanently ignored.

When exact current metric depth and calibrated point/frame evidence support the selected corridor basis, Guardian computes lateral offset, forward distance and signed boundary distance for PERSON, BICYCLE, MOTORCYCLE, CAR, BUS and TRUCK. The GROUNDED_CLASS_ASSUMPTION and HEIGHT_NOT_TESTED flags remain explicit. Other/unknown categories fall back to image relevance. Relative depth never enters the metric branch. A robust object-depth point is explicitly NOT a ground-contact point or full physical footprint. No class width priors, invented object radii, cuboids or blanket bbox-to-ground projection are used.

Otherwise, current image geometry uses bbox bottom-center and compact bbox/corridor overlap. The representative inside the boundary band is NEAR_BOUNDARY, inside is INSIDE, an intersecting bbox is INTERSECTS, otherwise OUTSIDE. All such results are IMAGE_SPACE_RELATION and expose no metric distances. Bottom-center is a visual representative only, including for unknown/non-grounded categories; no contact assumption is hidden.

Expired/lost, too-old, failed, wrong-source or otherwise unusable entity evidence yields UNKNOWN. Predicted image locations remain UNRELIABLE with their original source age. Metric results retain UNVALIDATED depth and point uncertainty rather than confidence probabilities. Future Task013 receives all entities and their relations; an outside entity may later cross the corridor.
