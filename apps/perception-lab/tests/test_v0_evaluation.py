"""Reference strata and denominators must resist optimistic evaluation artifacts."""

from dataclasses import replace

import pytest

from perception_lab.v0_evaluation import (
    STAGES,
    LabelStatus,
    StageOutcome,
    V0EventLedger,
    first_failure,
    quadrant,
    summarize_events,
)


def event(status=LabelStatus.PROXY, outcomes=None, event_id="one"):
    stages = tuple(StageOutcome(s, "PASS") for s in STAGES) if outcomes is None else outcomes
    failure, reason = first_failure(stages)
    return V0EventLedger(
        event_id,
        "session",
        0,
        10,
        status,
        True if status in {LabelStatus.PROXY, LabelStatus.HUMAN_REVIEWED} else None,
        "PERSON",
        "UNKNOWN",
        None,
        stages,
        failure,
        reason,
        None,
        "UNKNOWN",
        "UNKNOWN",
        "prototype annotated source",
    )


def test_drafts_cannot_become_headline_truth():
    row = event(LabelStatus.DRAFT)
    summary = summarize_events((row,))["DRAFT"]
    assert summary["events"] == 1
    assert summary["end_to_end"] == {"numerator": None, "denominator": None, "coverage": None}
    with pytest.raises(ValueError, match="Unresolved"):
        replace(row, relevant=True)


def test_failure_charged_once_and_downstream_pass_cannot_resurrect_funnel():
    stages = list(event().stages)
    stages[1] = StageOutcome("TRACK", "FAIL")
    row = event(outcomes=tuple(stages))
    result = summarize_events((row,))["PROXY"]
    assert result["first_failure_counts"] == {"TRACK": 1}
    assert result["end_to_end"]["coverage"] == 0
    assert result["conditional_stage_coverage"][3]["denominator"] == 0
    assert result["conditional_stage_coverage"][3]["coverage"] is None


def test_unknown_prevents_claiming_later_first_failure():
    stages = list(event().stages)
    stages[0] = StageOutcome("DETECTION", "UNKNOWN")
    stages[5] = StageOutcome("INTERACTION", "FAIL")
    assert first_failure(tuple(stages)) == ("DETECTION", "GROUND_TRUTH_LIMITATION")


def test_strata_and_duplicate_events():
    proxy, human = event(), event(LabelStatus.HUMAN_REVIEWED, event_id="two")
    result = summarize_events((proxy, human))
    assert result["PROXY"]["end_to_end"]["denominator"] == 1
    assert result["HUMAN_REVIEWED"]["end_to_end"]["denominator"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_events((proxy, proxy))


def test_ledger_rejects_inconsistent_failure_and_missing_stages():
    with pytest.raises(ValueError, match="First failure"):
        replace(event(), first_failure_stage="TRACK")
    with pytest.raises(ValueError, match="Every canonical"):
        replace(event(), stages=event().stages[:-1])


@pytest.mark.parametrize(
    "covered,timely,expected",
    [
        (True, True, "A_CORRECT_TIMELY"),
        (True, False, "B_CORRECT_LATE"),
        (False, True, "C_MISSED_TIMELY_PROCESSING"),
        (False, False, "D_MISSED_LATE"),
        (None, True, "UNKNOWN"),
        (True, None, "UNKNOWN"),
    ],
)
def test_quadrants_preserve_unknown(covered, timely, expected):
    assert quadrant(covered, timely) == expected


@pytest.mark.parametrize("age", [-1, 1.5, True])
def test_invalid_age_rejected(age):
    with pytest.raises(ValueError, match="timestamp/age"):
        StageOutcome("TRACK", "PASS", source_to_stage_age_ns=age)


@pytest.fixture
def evaluation_tools(monkeypatch):
    import importlib
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[3] / "tools"))
    return importlib.import_module("v0_analyze"), importlib.import_module("v0_review")


def test_blind_selection_deterministic_and_unlabeled(evaluation_tools, tmp_path):
    _, review = evaluation_tools
    source = tmp_path / "source.mp4"
    source.write_bytes(b"test source identity; no decoding needed for selection")
    first = review.prepare(source, tmp_path / "a")
    second = review.prepare(source, tmp_path / "b")
    assert first == second
    assert len(first["windows"]) == 30
    assert all(w["review_label"] is None for w in first["windows"])
    for left, right in zip(first["windows"], first["windows"][1:], strict=False):
        assert left["end_seconds"] < right["start_seconds"]
    assert first["windows"][0]["start_seconds"] >= 0
    assert first["windows"][-1]["end_seconds"] <= 600
    with pytest.raises(FileExistsError):
        review.prepare(source, tmp_path / "a")


def test_rescue_review_preserves_windows_without_creating_human_labels(evaluation_tools, tmp_path):
    _, review = evaluation_tools
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source identity")
    original = review.prepare(source, tmp_path / "original")
    packet = review.rescue_review(tmp_path / "original/manifest.json", tmp_path / "rescue")
    assert [(w["start_seconds"], w["end_seconds"]) for w in original["windows"]] == [
        (w["start_seconds"], w["end_seconds"]) for w in packet["windows"]
    ]
    assert not packet["human_review_complete"]
    assert all(
        w["review_label"] is None and w["interruption_label"] is None for w in packet["windows"]
    )
    assert "TOO_LATE" in packet["interruption_labels"]
    assert review.digest(tmp_path / "original/manifest.json") == packet["origin_packet_sha256"]


def test_async_trace_flushes_every_row(evaluation_tools):
    from io import StringIO

    from rescue_trace import AsyncTrace

    stream = StringIO()
    writer = AsyncTrace(stream)
    for i in range(10):
        writer.submit({"index": i})
    writer.close()
    assert writer.rows == 10
    assert writer.utf8_bytes == len(stream.getvalue().encode("utf-8"))
    assert writer.serialization_ns > 0
    assert writer.write_ns > 0
    assert len(stream.getvalue().splitlines()) == 10
    assert writer.peak <= 16
    with pytest.raises(RuntimeError, match="closed"):
        writer.submit({"late": 1})


def test_freshness_failure_identifies_decode_before_detector(evaluation_tools):
    from rescue_profile import first_failure

    row = {
        "due_monotonic_ns": 100,
        "timing": {"decode_started_ns": 100, "decode_completed_ns": 600_000_101},
        "components": [
            {"component_type": "detector", "started_ns": 700_000_100, "completed_ns": 800_000_100}
        ],
    }
    assert first_failure(row) == "decode"
    row["due_monotonic_ns"] = None
    assert first_failure(row) == "UNAVAILABLE_OFFLINE"


def test_freshness_failure_does_not_hide_uninstrumented_publication_tail(evaluation_tools):
    from rescue_profile import first_failure

    assert (
        first_failure({"due_monotonic_ns": 0, "publication_monotonic_ns": 500_000_001})
        == "publication"
    )


def test_async_trace_overflow_and_io_failure_are_not_silent(evaluation_tools):
    from threading import Event

    from rescue_trace import AsyncTrace

    entered, release = Event(), Event()

    class FailingStream:
        def write(self, text):
            entered.set()
            assert release.wait(5)
            raise OSError("disk failure")

        def flush(self):
            pass

    writer = AsyncTrace(FailingStream())
    try:
        writer.submit({"first": 1})
        assert entered.wait(5)
        for i in range(16):
            writer.submit({"queued": i})
        with pytest.raises(RuntimeError, match="capacity exhausted"):
            writer.submit({"overflow": 1})
    finally:
        release.set()
    with pytest.raises(RuntimeError, match="Trace writer failed"):
        writer.close()


def test_linked_funnel_cannot_use_different_object(evaluation_tools):
    analyze, _ = evaluation_tools
    annotation = {"label": "PERSON", "box": [0, 0, 10, 10]}
    box = dict(zip(("x1", "y1", "x2", "y2"), annotation["box"], strict=True))
    row = {
        "detector": {"detections": [{"label": "PERSON", "box": box}]},
        "tracks": {
            "tracks": [
                {
                    "category": "PERSON",
                    "observation_status": "OBSERVED",
                    "bbox": box,
                    "track_id": {"serial": 1},
                }
            ]
        },
        "world": {"entities": [{"source_track_id": {"serial": 2}, "entity_id": {"serial": 3}}]},
    }
    flags, track = analyze.linked_stages(row, annotation)
    assert track == {"serial": 1}
    assert flags[:3] == [True, True, False]
    assert not any(flags[3:])


def test_source_mismatch_fails_closed(evaluation_tools, tmp_path):
    import json

    analyze, _ = evaluation_tools
    (tmp_path / "manifest.json").write_text(
        json.dumps({"status": "COMPLETE", "source_sha256": "a"})
    )
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"source_sha256": "b"}))
    with pytest.raises(ValueError, match="source hash"):
        analyze.analyze(tmp_path, references)


def test_analyzer_rejects_partial_run(evaluation_tools, tmp_path):
    import json

    analyze, _ = evaluation_tools
    (tmp_path / "manifest.json").write_text(json.dumps({"status": "RUNNING"}))
    with pytest.raises(ValueError, match="incomplete"):
        analyze.analyze(tmp_path, tmp_path / "not_needed.json")


def test_exact_quantiles_and_degenerate_iou(evaluation_tools):
    analyze, _ = evaluation_tools
    assert analyze.quantiles([])["p95_ns"] is None
    assert analyze.quantiles([5, 1, 2, 4, 3])["p50_ns"] == 3
    assert analyze.iou({"x1": 0, "y1": 0, "x2": 0, "y2": 0}, [0, 0, 0, 0]) == 0


def test_analysis_writes_artifacts_with_alert_outputs(evaluation_tools, tmp_path):
    import json

    analyze, _ = evaluation_tools
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "source_sha256": "a",
                "requested_seconds": 1,
            }
        )
    )
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps({"source_sha256": "a", "frames": []}))
    row = {
        "identity": {"observation_ns": 0, "sequence": 0},
        "publication_monotonic_ns": 10,
        "due_monotonic_ns": None,
        "spans": [],
        "components": [],
        "source_to_publication_age_ns": None,
        "attention_candidates": [],
        "alert_output_set": {"outputs": [{"status": "NO_PRESENTATION", "delivered": False}]},
    }
    (tmp_path / "updates.jsonl").write_text(json.dumps(row) + "\n")
    report = analyze.analyze(tmp_path, refs, output=tmp_path / "analysis")
    assert report["alerts"]["text_sink_accepted"] == 0
    assert report["updates"] == 1
    assert (tmp_path / "analysis" / "event-ledger.jsonl").is_file()
    assert json.loads((tmp_path / "analysis" / "analysis.json").read_text())["source_ages"] == {}
