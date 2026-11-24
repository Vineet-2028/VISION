# Alert architecture

IMPLEMENTED: optional `alerts` pipeline stage after AttentionEngine. Only selected attention decisions can become intents. No detector, tracker, world, trajectory, risk computation, network, ML or platform audio dependency is added. Frozen AlertIntent separates meaning from frozen AlertPresentation. AlertRenderer and AlertPresenter are replaceable protocols. Single pipeline-thread ownership; sinks must be bounded and nonblocking.

Current producers do not authorize category, direction or crossing/approaching semantics. They therefore produce the honest generic phrase `Object.` for selected interruptions. Optional AttentionSemanticEvidence supports future upstream facts with matching entity/session, timestamps, quality and provenance. Bare legacy category/direction strings are not sufficient authority. The renderer never examines bounding boxes.

Task016 conditional entity-episode coverage was 3.98%; Task014 tracker-proxy interaction recall was 5.8%. These are different denominators and must not be multiplied or described as hazard recall. All Task016 realtime candidates expired. Wording cannot recover missed or stale upstream evidence.

PROVISIONAL: English phrasing, age and speech-rate parameters. UNVALIDATED: human comprehensibility/usefulness, physical quantities, hazard recall and production safety. PLANNED: actual speech, haptics, personalization and localization. Task018 is not implemented.

Enable `"alerts": {}` in an existing detector/tracker/world/risk/attention configuration. `configs/perception-lab.alerts.example.json` is a minimal stage-wiring example with placeholder footage and synthetic calibration/segmentation; it does not create tracked entities or qualify geometry. No arbitrary path in an example is an installed dataset.
