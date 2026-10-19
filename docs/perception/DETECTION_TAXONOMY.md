# Detection taxonomy

Version: sentinel-coco-p0-v1.

| Canonical class | COCO annotation ID | COCO-80 model index | Group      |
| --------------- | -----------------: | ------------------: | ---------- |
| PERSON          |                  1 |                   0 | PEDESTRIAN |
| BICYCLE         |                  2 |                   1 | VEHICLE    |
| CAR             |                  3 |                   2 | VEHICLE    |
| MOTORCYCLE      |                  4 |                   3 | VEHICLE    |
| BUS             |                  6 |                   5 | VEHICLE    |
| TRAIN           |                  7 |                   6 | VEHICLE    |
| TRUCK           |                  8 |                   7 | VEHICLE    |
| DOG             |                 18 |                  16 | ANIMAL     |

These eight classes form the current P0 research scope. Train is retained for crossings; dog is the supported animal baseline. Other source names map to UNKNOWN while retaining their original ID/name. Do not confuse sparse annotation IDs with contiguous model indices.

CYCLIST and STATIC_OBJECT are reserved groups. Neither person nor bicycle detection establishes that a person is riding. Chair/bench are not P0 without product evidence. A moving/static classification cannot be inferred from one image.

Generic pretrained detection does not reliably cover poles, bollards, potholes, curbs, stairs, drains, overhanging branches or glass doors. Segmentation should describe surfaces and traversability; depth should estimate proximity with explicit uncertainty; flow/tracking should establish temporal correspondence; physics should estimate velocity/TTC/CPA. None of these measurements is fabricated by this detector.
