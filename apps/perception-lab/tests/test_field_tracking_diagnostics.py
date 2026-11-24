from dataclasses import asdict

from test_tracking import detection, tracker, update

from perception_lab.field_tracking_diagnostics import DiagnosticTracker


def test_observer_preserves_assignment_and_reports_exact_distance_gate():
    baseline = tracker()
    observed = DiagnosticTracker(baseline.config, "session", "clock", 640, 480)
    for stamp, detections in [(0, [detection()]), (100, [detection(11)]), (200, [detection(500)])]:
        assert asdict(update(baseline, stamp, detections)) == asdict(
            update(observed, stamp, detections)
        )
    assert observed.diagnostic["source_sequence"] == 200
    assert observed.diagnostic["cost_observations"][0]["reason"] == "CENTER_DISTANCE_GATE"
    assert observed.diagnostic["first_confirmed_failure_stage"] == "UNKNOWN"


def test_cost_observation_budget_does_not_change_matching():
    baseline = tracker()
    observed = DiagnosticTracker(baseline.config, "session", "clock", 640, 480)
    objects = [detection(i * 30) for i in range(15)]
    for stamp in (0, 100):
        assert asdict(update(baseline, stamp, objects)) == asdict(update(observed, stamp, objects))
    assert len(observed.diagnostic["cost_observations"]) == 64
    assert observed.diagnostic["truncated"]
