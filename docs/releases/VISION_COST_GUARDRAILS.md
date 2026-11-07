# Cost and resource guardrails

Current authorized cloud spend: **0**. No resources or paid accounts were created.
The website is static; local phone sessions use the existing PC. No always-on GPU,
automatic footage upload, training job or cloud history API is enabled.

Use this worksheet before any separately authorized cloud experiment. Obtain current
provider prices and taxes when choosing a provider; no advertised free tier is a
permanent cost guarantee.

| Component          | Calculation                                                | Current allocation |
| ------------------ | ---------------------------------------------------------- | ------------------ |
| Storage            | average retained GB × monthly GB price                     | 0 cloud GB         |
| Object operations  | uploads/reads/deletes × operation unit price               | 0                  |
| Transfer           | billable outbound GB × transfer price                      | 0                  |
| GPU                | GPU count × maximum job hours × hourly price               | 0 hours            |
| API / DB           | requests, compute, storage and backups × applicable prices | 0                  |
| Monitoring / taxes | logs, retention, alerts and applicable taxes               | 0                  |

A later owner-approved monthly ceiling is required before remote activation. Configure
alerts at 50/80/100%, but do not call billing alerts hard limits. Enforce application
quotas, bucket retention and upload-disable switches, a per-job wall-time limit and
an actual GPU shutdown action. Include versioned objects, backups and deletion lag
in storage estimates. Start with one provider per function, not a microservice fleet.

Local guardrails: reserve at least 2 GiB RAM, bounded latest-frame admission, small
history storage, and no unnecessary GPU replay for product UI changes. Before any
future GPU run, state its expected duration, stop condition and resource ceiling.
Task019 on-device ORT/NNAPI/XNNPACK and quantization require separate per-device
thermal, battery, latency, accuracy and lifecycle qualification. They are not
implemented by this marketing or wireless product pass.
