# Prototype risk levels and rules

IMPLEMENTED deterministic precedence, after source validation:

| Evidence                                                                                              | Level        |
| ----------------------------------------------------------------------------------------------------- | ------------ |
| Fresh observed current corridor occupancy                                                             | HIGH         |
| Same occupancy with all usable forecasts receding                                                     | ELEVATED     |
| Usable nominal predicted entry within configured urgent horizon (default 1 second)                    | HIGH         |
| Later usable nominal predicted entry                                                                  | ELEVATED     |
| Usable possible envelope-only entry                                                                   | ELEVATED     |
| Fresh observed outside relation and usable forecasts all remain outside with no envelope intersection | LOW          |
| Otherwise                                                                                             | UNDETERMINED |

SEVERE is reserved and never emitted by this baseline. LOW is lower modeled relevance, never safety. A stationary inside obstacle needs no TTC, depth or semantics to receive HIGH. No class implies a level. Receding inside remains ELEVATED. A parallel outside case ranks below equivalent crossing. Unknown geometry and missing future evidence cannot support LOW.

PROVISIONAL: thresholds are fixed before evaluation; sensitivity runs use 0.5/1/2 second entry thresholds, without selecting a winner using this development footage. Predicted-only or stale track state cannot support current occupancy or future-risk ranking. All levels expire after the configured validity interval (default 500 ms).
