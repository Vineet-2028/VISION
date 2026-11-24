"""Build a byte index into the measured Alpha trace without copying camera or trace data."""

import argparse
import hashlib
import json
from pathlib import Path


def build(run, output):
    manifest = json.loads((run / "manifest.json").read_text())
    if manifest["status"] != "COMPLETE" or manifest["trace_mode"] != "COMPACT_ALPHA_TRACE":
        raise ValueError("Expected completed Alpha replay")
    trace = run / "updates.jsonl"
    before = trace.stat()
    entries = []
    checksum = hashlib.sha256()
    offset = 0
    with trace.open("rb") as source:
        for line in source:
            row = json.loads(line)
            pts = row["identity"]["observation_ns"]
            if (entries and pts <= entries[-1][0]) or len(line) > 4_000_000:
                raise ValueError("Invalid replay row")
            entries.append([pts, offset, len(line)])
            checksum.update(line)
            offset += len(line)
    if (
        trace.stat().st_mtime_ns != before.st_mtime_ns
        or offset != before.st_size
        or len(entries) != manifest["trace_writer"]["rows"]
    ):
        raise ValueError("Trace changed or incomplete")
    with output.open("x", encoding="utf-8") as result:
        json.dump(
            {
                "schema_version": 1,
                "source_sha256": manifest["source_sha256"],
                "size": offset,
                "mtime_ms": before.st_mtime_ns / 1e6,
                "trace_sha256": checksum.hexdigest(),
                "entries": entries,
            },
            result,
            separators=(",", ":"),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.run, args.output)
