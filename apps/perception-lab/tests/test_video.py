from fractions import Fraction

import av
import numpy as np
import pytest

from perception_lab.cli import main
from perception_lab.contracts import Frame, LabError, TimingProvenance
from perception_lab.sources import VideoFileSource


def generate_video(path):
    with av.open(str(path), "w") as container:
        stream = container.add_stream("ffv1", rate=25)
        stream.width, stream.height = 8, 6
        stream.pix_fmt = "bgr0"
        stream.time_base = Fraction(1, 1000)
        stream.codec_context.time_base = Fraction(1, 1000)
        for timestamp in (0, 40, 120, 160):
            frame = av.VideoFrame.from_ndarray(np.zeros((6, 8, 3), dtype=np.uint8), format="rgb24")
            frame.pts, frame.time_base = timestamp, Fraction(1, 1000)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def test_real_decoder_vfr_end_to_end(make_pipeline, tmp_path):
    path = tmp_path / "tiny.mkv"
    generate_video(path)
    source = VideoFileSource(path, "synthetic", 100)
    try:
        frames = list(source)
        assert all(isinstance(f, Frame) for f in frames)
        assert [f.identity.observation_ns for f in frames] == [
            0,
            40_000_000,
            120_000_000,
            160_000_000,
        ]
        assert all(f.identity.timing == TimingProvenance.AUTHORITATIVE_PTS for f in frames)
    finally:
        source.close()
    pipeline, recorder = make_pipeline({"record_session": True})
    source = VideoFileSource(path, "synthetic", 100)
    result = pipeline.run(source)
    assert result["summary"]["frame_counts"]["processed"] == 4
    assert result["summary"]["frame_counts"]["dropped"] == 0
    assert source.closed and recorder.closed
    path.unlink()  # Windows fails this if decoder leaves file handle open.


def test_invalid_video_and_cli_failure_sanitized(tmp_path, capsys):
    path = tmp_path / "private-person.mkv"
    path.write_bytes(b"not video")
    with pytest.raises(LabError, match="SOURCE_OPEN_FAILED"):
        VideoFileSource(path, "synthetic", 100)
    path.unlink()
    assert main(["replay", "--config", str(path)]) == 1
    assert "private-person" not in capsys.readouterr().err


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exit:
        main(["replay", "--help"])
    assert exit.value.code == 0
    assert "--record-session" in capsys.readouterr().out
