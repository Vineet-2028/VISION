# Versioned semantic ontology

The small domain group set is data-backed by
`configs/perception/ontology/vision-domain-v1.json`. It separates useful display
and analysis categories from detector-specific labels. UNKNOWN is explicit.
Group membership is not a physical grounding assertion or a risk threshold.

The initial ontology defines broad group anchors and descriptions. It deliberately
does not claim to classify arbitrary breed/model names. External licensed hierarchy
ingestion and text-embedding comparison are still pending. An unrecognized concept
resolves to UNKNOWN with zero asserted semantic confidence.

`HierarchyConceptResolver` validates the complete bounded hierarchy at load time:
262144 bytes, 4096 nodes, 64 anchors per group and 32 ancestry steps. Duplicate
keys, ambiguous anchors, cycles, unresolved roots and malformed groups fail before
runtime. Resolution is a precomputed lookup; no text encoder runs per frame.

The payload hash and ontology/resolver versions identify the mapping. Resolver
confidence retains input concept confidence; it does not create evidence that
the provider recognized an object correctly. No ontology value is executable.

Concept normalization uses explicit Unicode normalization and case folding,
bounded lengths and control-character rejection. Raw labels remain provenance;
they are not automatically eligible for speech. Reliable/stable spoken-label
selection and embedding-based mapping still need separate evaluation.
