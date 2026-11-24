from perception_lab.field_case_ledger import case_ledger


def test_later_publication_joins_exact_source_without_claiming_physical_success():
    packet = {
        "sequence": 7,
        "camera_ns": "100",
        "rotation": 90,
        "recorded_events": [{"kind": "FRAME_ADMITTED", "rotation": 90}],
        "detector_source_events": [
            {
                "sequence": 9,
                "detector_diagnostics": {"source_id": "session", "source_sequence": 7},
                "object_diagnostics": {
                    "objects": [
                        {
                            "source_frame": {"source_id": "session", "sequence": 7},
                            "entity_id": "entity",
                            "track_id": "track",
                            "semantics": {"state": "UNKNOWN"},
                        },
                        {
                            "source_frame": {"source_id": "other", "sequence": 7},
                            "entity_id": "wrong",
                        },
                    ]
                },
            }
        ],
        "delivery_events": [{"kind": "TTS_ERROR", "alert_id": "linked"}],
    }
    result = case_ledger(packet, "session")
    stages = result["stages"]
    assert stages["DETECTOR_SOURCE"]["references"] == [
        "/detector_source_events/0/detector_diagnostics"
    ]
    assert stages["WORLD"]["references"] == [
        "/detector_source_events/0/object_diagnostics/objects/0/entity_id"
    ]
    assert stages["TTS_CALLBACK"]["references"] == ["/delivery_events/0"]
    assert stages["PRE_NMS"]["availability"] == "EVIDENCE_NOT_AVAILABLE"
    assert result["first_confirmed_failure_stage"] == "UNKNOWN"
    assert result["reference_object_identity"] == "NO_REFERENCE_OBJECT_IDENTITY"
    assert packet["detector_source_events"][0]["sequence"] == 9


def test_stage_reference_count_is_bounded_and_reports_omissions():
    packet = {
        "sequence": 1,
        "camera_ns": "100",
        "rotation": 0,
        "recorded_events": [{"kind": "FRAME_ADMITTED", "rotation": 0}] * 100,
    }
    result = case_ledger(packet, "session")
    assert len(result["stages"]["ADMISSION"]["references"]) == 16
    assert result["references_omitted"] == 168
