# Sentinel surface taxonomy v1

Version: `sentinel-surfaces-v1`. Native predicted masks use uint8, UNKNOWN=0. Annotation-only IGNORE=255 is excluded from metrics and rejected as a prediction. IDs are immutable for this version; future migrations must name source and destination versions and preserve historical masks.

| ID  | Class            |
| --- | ---------------- |
| 0   | UNKNOWN          |
| 1   | SIDEWALK         |
| 2   | ROAD             |
| 3   | FLOOR            |
| 4   | PATH             |
| 5   | STAIRS           |
| 6   | GRASS            |
| 7   | VEGETATION       |
| 8   | WALL             |
| 9   | BUILDING         |
| 10  | CURB             |
| 11  | GROUND_OTHER     |
| 12  | PERSON           |
| 13  | BICYCLE          |
| 14  | MOTORCYCLE       |
| 15  | VEHICLE          |
| 16  | POLE             |
| 17  | FENCE            |
| 18  | OBJECT_OTHER     |
| 19  | BACKGROUND_OTHER |

Higher groups: ground surface, structure, dynamic object, static obstacle, vegetation and unknown. Group membership never implies traversability or safety.

Cityscapes mapping v1: road/sidewalk/building/wall/fence/pole map directly; traffic lights/signs become OBJECT_OTHER; vegetation remains VEGETATION; terrain becomes broad GROUND_OTHER, not GRASS; sky becomes BACKGROUND_OTHER; person/rider become PERSON; car/truck/bus/train become VEHICLE; motorcycle/bicycle map directly. FLOOR, PATH, STAIRS, CURB and GRASS are unsupported by these checkpoints. Unsupported classes stay explicit in each provider's supported-class set. Taxonomy coverage is a known product gap.
