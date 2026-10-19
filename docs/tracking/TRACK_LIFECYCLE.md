# Track lifecycle

IMPLEMENTED transitions:

| Event                                                             | State/result                                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Unmatched detection at publication score                          | TENTATIVE, new session-local serial                                       |
| Configured consecutive successful hits within confirmation window | CONFIRMED                                                                 |
| Successful detector update without a match                        | Established track LOST; miss counters increment                           |
| Detector not scheduled                                            | Predict, preserve lifecycle; no invented detector miss                    |
| Recoverable detector failure/unavailable output                   | Predict; retain failure/degraded quality; no successful-empty evidence    |
| Match before timeout                                              | CONFIRMED if previously confirmed; otherwise tentative confirmation rules |
| Observation timeout or tentative confirmation timeout exceeded    | REMOVED ID emitted once; state freed                                      |

`OBSERVED` means matched/born on this update; `PREDICTED` means no observation at the
state timestamp. Latest-observed time/box and current state/predicted box are separate.
Expiry is source-time based, default one second, not frame-count based. At the exact
deadline a track may still match; after it, a returning object receives a new ID.

Confirmation defaults to three consecutive successful hits within one second.
Unscheduled ticks do not break a hit streak; a successful empty/missed update does.
Low-confidence recovery only matches previously confirmed tracks and never births
or promotes a tentative track. Values are research parameters, not production policy.

Quality is last detector score × association quality × linear recency × failure
penalty. It is an uncalibrated quality proxy, not probability or hazard severity.
Prediction age is explicit; failure evidence persists until a successful match.
Category votes decay by .8 per matched observation, then add that observation's
score. A single flip usually does not change the category, but accumulated evidence can.

Ambiguous overlapping/crossing objects can still switch identities. No probabilistic
merge/split, long-term identity recovery or appearance recognition is claimed.
