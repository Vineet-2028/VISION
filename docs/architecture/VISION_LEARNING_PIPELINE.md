# Offline learning foundation — no training performed

Local collection and optional useful/not-useful feedback do not grant research
consent. Explicit input requires current `MODEL_RESEARCH` grants, provenance,
scenario tags, redaction review and independent label attestations. Review all
selection categories: alerts, silence, missed important events and capability
changes. Model pseudo-labels remain proposals until independently inspected.

`product_data.py` validates contracts, rejects conflicting grants/self-review/
reviewer disagreement, deduplicates hashes and groups every connected participant,
route or session into a single split. Adjacent or linked samples cannot leak between
splits. Hash buckets target 70/15/15; small datasets may have empty held-out splits
and are not training-qualified. Adding linked data can change group assignments:
freeze and compare dataset versions rather than assuming append-only stable splits.

```powershell
$privateResearch = Join-Path $env:LOCALAPPDATA 'VISION\private-data'
New-Item -ItemType Directory -Force -Path $privateResearch | Out-Null
.\apps\perception-lab\.venv\Scripts\python.exe tools/product_dataset.py "$privateResearch\review-input.json" "$privateResearch\reviewed-manifest.json" --registry "$privateResearch\registry.sqlite" --objects "$privateResearch\objects"
```

Place the approved input in that private directory. For this OneDrive checkout,
keep real research inputs, manifests and exports outside synchronized folders.
Input JSON contains `artifacts`, `reviews`
and `grants` matching the typed contracts. The command refuses to overwrite an
export, consults the persistent withdrawal ledger, and never uploads or trains.
The hash covers the canonical manifest, not the separately appended review queue.
Before any downstream use, retrieve the version with `DatasetRegistry.manifest` and
recheck current grant expiry; old exported files cannot establish current consent.
Withdraw using `DatasetRegistry.withdraw(participant)`; reopen and call
`reconcile_deletions()` to finish interrupted physical deletion.

## Experiment protocol

Freeze input/source hashes, frame clocks, model/config/runtime hashes, reviewed labels,
reviewer provenance and group splits. Use image recognition for identity; tracking
and flow for motion. A future event-clip teacher is optional offline research, not
a new production model family. Keep unknown labels and missing context explicit.
Evaluate baseline and candidate on identical source identities, including silence.
Report relevance, missed important events, nuisance interruptions, timing, abstention,
scenario coverage, latency P50/P95/P99, memory and reviewer disagreement.

Candidate registry records must bind dataset version, artifact SHA-256, license,
runtime/config hashes, paired report, approval state and rollback target. Initially
all candidates are SHADOW_ONLY; only the existing frozen release is runnable by
Guardian. Rollback means selecting the previously qualified artifact/config pair,
never silently substituting a downloaded model. Training and promotion commands
are intentionally absent until independent reviewed data and physical gates exist.

`DatasetRegistry.export_reviewed` verifies current consent and membership of the
artifact in the reviewed version. It persists a quota reservation and export intent
before invoking `PrivateS3Export`. Configure the SDK client with HTTPS, SigV4, short timeouts,
bounded retries and narrowly scoped credentials. Signed reads expire within five
minutes; no signed upload endpoint or public ACL is provided. Real-cloud isolation,
aggregate quotas and deletion verification remain prerequisites, not tested claims.
See the [lifecycle](VISION_DATA_LIFECYCLE.md) and cost guardrails.

References: [official SDK presigning API](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/generate_presigned_url.html),
[presigned URL guardrails](https://docs.aws.amazon.com/prescriptive-guidance/latest/presigned-url-best-practices/additional-guardrails.html).
