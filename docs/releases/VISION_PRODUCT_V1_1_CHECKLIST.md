# Product V1.1 local release checklist

Scope covers the public website, private Lab, wireless phone client, opt-in event history and offline research foundation. The physical acceptance record remains open. The target proposal and nine architecture decisions are indexed in [the implementation decisions](../architecture/IMPLEMENTATION_DECISIONS.md).

| Gate                 | Executed result or outstanding evidence                                                                                                                                                                                                                                     |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frozen engine        | Verified the original release manifest SHA-256, 107 qualified source files and both model hashes. The historical long replay measured 12.368 updates/s and 241.947 ms P95 publication age over 18,541 updates. These are recorded Windows replay measurements.              |
| Public site          | Production build and separate eight-page static export passed. Export scans for private routes, media, credentials interface names and model assets. The text demo supports an interruption and a silent outcome.                                                           |
| Private Lab          | Production HTTP smoke exercised anonymous rejection, login, private replay-page access and authenticated raw-media denial with media disabled.                                                                                                                              |
| Web tests            | ESLint, strict TypeScript and 42 tests passed. Browser QA exercised navigation, the decision toggle and keyboard expansion of recorded reasons.                                                                                                                             |
| Responsive layout    | Actual browser screenshots at widths 360, 390, 768, 1280 and 1440. The homepage had zero horizontal overflow at all five widths. The mobile demo had one main landmark and one top-level heading.                                                                           |
| Gateway and research | Full Python lab run passed 1,354 tests. Real loopback TLS tests cover certificate trust, expiry/rotation and revocation alongside pairing and session policy tests. Storage tests cover consent gates, deduplication, split isolation, withdrawal and interrupted deletion. |
| Backend and Guardian | Maven verification passed 195 Guardian and three Spring health tests. Production smoke exercised eight concurrent health requests and a backend outage.                                                                                                                     |
| Android software     | Debug APK and instrumented test APK built. Ten JVM tests and Android lint passed. The device suite uses isolated SQLite files, preferences and encryption aliases.                                                                                                          |
| Security advisories  | npm audit reported zero advisories at verification time. The result applies to the npm dependency graph.                                                                                                                                                                    |
| Data and cost        | Local storage is the default. Remote SDK contract tests used a fake client. Authorized cloud budget is zero. No training or public deployment was performed.                                                                                                                |

Local logs and browser captures are under `benchmark-results/v02/product-*`. For the public preview and the private operator setup, see [web deployment](VISION_PUBLIC_WEB_DEPLOYMENT.md). For phone setup, use [the wireless field guide](VISION_WIRELESS_ALPHA_FIELD_GUIDE.md).

The final wireless launcher smoke test started the frozen profile on loopback. Its
operator page generated a QR carrying the trusted certificate. An HTTPS client
exchanged the code once, obtained a session token and lost access after operator
revocation. See `product-wireless-entrypoint-final.log`. This check opened no camera
session and used no GPU time.

For the desktop before/after comparison, the saved pre-task patch reproduced
homepage, layout and CSS Git blobs `b1ebbc9`, `c296177` and `aac24b6`. Both
versions were rendered in the browser at 1280 Ã— 900. The captures are
`product-ui/before-1280.jpg` and `product-ui/after-1280.jpg`. The final static
export navigated from home to the interactive demo on a plain HTTP file server.

The feature branch includes the existing qualified Python engine dependencies.
All 106 staged engine Python blobs matched their original manifest hashes. The
other qualified engine source entry is the locally built Guardian JAR. Fourteen
Python paths require byte-preserving Git attributes because line-ending conversion
would change their release hashes. Private evidence, weights, APKs and local
credentials stay outside the release commits.

The final `npm run verify` completed through the production HTTP smoke check.
The authenticated private-runtime probe also retrieved 18,541 indexed timestamps,
the first selected frame packet and all 30 review windows with raw media disabled.
The final Android build finished in 57 seconds with at least 2.54 GiB of RAM free.
The debug APK SHA-256 is `c7d7ee016e820b9243eaeebeb0056dce7903bc5a9f163112f05617bca6c96874`.

## Outstanding acceptance

- `adb devices` returned an empty device list. Record a physical same-LAN pairing, camera timestamp behavior, Bluetooth delivery, network loss, Stop/background behavior, storage migration/deletion and reinstall on the target phone.
- A real screen-reader session and a matched before/after phone screenshot pair are outstanding. Saved browser screenshots document the current public site. The earlier private footage stays in restricted local evidence.
- Public domain, host preview, hosted security headers, real private storage policies, remote quotas and deletion reconciliation require a separately approved target. The public artifact is available locally.
- Independent human usefulness and physical safety validation remain open. Standalone Android inference requires a separate milestone and per-device qualification.
- This checkout contains historical Task001â€“018 work predating this release. Validate a clean checkout with its approved runtime assets before publishing a reproducible release tag.
