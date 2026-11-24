# English V1 vocabulary — PROTOTYPE / UNVALIDATED

| Input category                                | Noun       |
| --------------------------------------------- | ---------- |
| PERSON                                        | Person     |
| BICYCLE                                       | Bicycle    |
| MOTORCYCLE                                    | Motorcycle |
| CAR / BUS / TRUCK / VEHICLE                   | Vehicle    |
| Authorized OBSTACLE                           | Obstacle   |
| Missing, unsupported or insufficient category | Object     |

| Authorized interaction / direction                          | Template                           |
| ----------------------------------------------------------- | ---------------------------------- |
| CROSSING + LEFT/RIGHT                                       | [Noun] crossing from [left/right]. |
| CROSSING + AHEAD                                            | [Noun] crossing ahead.             |
| CROSSING + UNKNOWN                                          | [Noun] crossing.                   |
| APPROACHING + LEFT/RIGHT/AHEAD                              | [Noun] approaching [direction].    |
| APPROACHING + UNKNOWN                                       | [Noun] approaching.                |
| GENERIC / IN_CORRIDOR / STATIC_OBSTACLE + known direction   | [Noun] [direction].                |
| GENERIC / IN_CORRIDOR / STATIC_OBSTACLE + unknown direction | [Noun].                            |

Current occupancy alone does not establish stationarity, bearing, crossing or approach. Current real evidence therefore uses generic `Object.`. Explicit future semantics are required for stronger examples.

ANNOUNCE and REPEAT use the complete phrase. ESCALATE preserves exactly the same facts with EMPHASIS metadata. No pronouns, navigation, collision certainty, safety verdict, model terminology, physical distances, speed or TTC. The 360-case matrix covers 6 categories × 4 directions × 5 interactions × 3 actions. All phrases are 1–5 words. Default 180 words/min gives approximately 0.33–1.67 seconds; this ignores articulation/startup and is not measured TTS duration. Single-word unknown fallback intentionally falls below the 2–6-word UX goal rather than adding unsupported facts.

Limits are 6 words and 64 characters by default; overflow rejects rather than truncates meaning. Category/direction maps and templates are versioned named choices, not arbitrary user-injected text.
