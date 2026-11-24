# V0 demo and field harness: pre-task audit

27 October 2026. Scope is a local presentation and transport harness. Original
Task019 on-device inference is excluded. The rescue report remains authoritative.

The existing web application is Next.js 16.4.2, React 19.2, strict TypeScript 5.9
with Vitest and ESLint. It contains a home and health page. The API is Spring Boot
4.1.1 on Java 21 and remains a stateless web backend. The perception lab is Python
3.12 with typed domain contracts, pytest, NumPy, PyAV, JPype and OpenCV. No Android
app or Android SDK was found in the initial workspace/default SDK location.

The selected rescue configuration, demo manifest, original JSONL and runtime source
hashes are frozen in the ignored `benchmark-results/v0-field/frozen-v0.json`.
The export contains original source PTS, dimensions, detections, tracks, decision
stages and alert presentations. Its mode is REALTIME because it records a realtime
experiment; playing it on the website is OFFLINE_REPLAY, never a new live result.
The video remains locally selected; no imagery is copied into public web assets.

The source recording uses 1906×876 image coordinates. Overlay transforms must
account for video letterboxing. JSONL is large: index offsets and serve bounded
individual states instead of loading the entire raw file into browser memory.

The alert deadline belongs to its source/session timeline. Phone and host raw
nanoseconds cannot be subtracted. The wire protocol uses decimal strings for
nanoseconds, a bounded four-timestamp exchange and explicit uncertainty. Unknown
clock quality prevents speech. Arrival time never replaces capture time.

Integration choice: bounded HTTP binary frame requests directly to a local Python
gateway, with authenticated result polling for Android and the browser. Spring
Boot does not relay images. Runtime work is isolated from request handling and
browser pacing; one active frame and one replaceable pending frame are the limit.
Loopback is the default. LAN exposure requires an explicit flag and session token.

Existing `npm run verify` covers formatting, Guardian, Python, web, API, security
and runtime smoke checks. The last frozen run passed 1,277 tests. New checks must
extend this gate. Hardware camera, Bluetooth and acoustic timing are not implied
by a successful build or synthetic test. Human review answers remain untouched.
