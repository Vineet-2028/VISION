import numpy as np

from perception_lab.field_detector_diagnostics import ObservedSession, summarize_vendor_output


def test_threshold_equality_survives_and_vendor_losses_remain_unknown():
    rows = np.array([[0, 0.49, 1, 2, 3, 4], [1, 0.5, 1, 2, 3, 4], [-1, 0, 0, 0, 0, 0]])
    result = summarize_vendor_output(rows, 0.5)
    assert result["vendor_output_count"] == 2
    assert result["adapter_score_rejected_count"] == 1
    assert result["adapter_score_survivor_count"] == 1
    assert result["nms_rejected_count"] is None
    assert result["raw_pre_nms_count"] is None


def test_rejected_samples_are_bounded():
    rows = np.tile([0, 0.1, 1, 2, 3, 4], (1000, 1))
    result = summarize_vendor_output(rows, 0.5)
    assert result["adapter_score_rejected_count"] == 1000
    assert len(result["rejected_samples"]) == 16
    assert result["rejected_samples_truncated"]


def test_observer_returns_exact_vendor_output_object():
    output = [np.array([[0, 0.8, 1, 2, 3, 4]])]

    class Session:
        def run(self, names, inputs):
            return output

    class Owner:
        confidence = 0.5

    owner = Owner()
    assert ObservedSession(Session(), owner).run(None, {}) is output
    assert owner.diagnostic["adapter_score_survivor_count"] == 1
