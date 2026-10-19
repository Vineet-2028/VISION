# Object depth sampling

IMPLEMENTED: central ROI, eroded ROI, lower-center ROI, near-surface percentile and bottom-center patch. No center-pixel-only distance. Default eroded box uses configurable 0.15 inset and a bounded 16x16 grid; these are provisional research parameters.

Each sample preserves the actual region, identity, representation, provider, median/P25/P75/MAD, valid fraction and attempted sample count. Invalid fraction below the policy threshold returns unavailable. Off-image boxes are unavailable rather than silently cropped.

Near-surface uses P25 for larger-is-farther and P75 for larger-is-nearer. Median is the default statistic. The default nearest grid is vectorized through Guardian's affine mapping basis; optional bilinear follows strict invalid-neighbor handling.

Sampling is generic, not a class-specific surface classifier. Background contamination, holes, occlusion and tiny boxes remain limitations. Repeated grid hits on the same low-resolution depth pixel are not independent evidence. Model confidence is not fabricated. Strategies must be compared on real observations; lower dispersion is not proof of correctness.
