# Initial architecture

Status: web-only foundation. Guardian is disabled; no monitoring is active.
The independent desktop [perception laboratory](perception/PERCEPTION_LAB_ARCHITECTURE.md)
supports local replay with optional research detectors. NoOp remains the default.
It does not add perception to the web/API.

## Runtime boundaries

```text
Browser -> Next.js server -> Spring Boot health endpoints

Reserved infrastructure: PostgreSQL | Redis | MinIO
```

The web uses Next.js App Router and strict TypeScript. Its server checks API
readiness without caching and cancels the request after three seconds. Network,
HTTP, or response-contract failures yield an explicit unavailable status.
Production requires `API_BASE_URL` at health-page request time; development defaults
to loopback. Invalid configuration raises a sanitized error separately from outages.

The Java 21 / Spring Boot API exposes typed health responses through Spring MVC.
Framework code remains inside `apps/api`. PostgreSQL, Redis, and MinIO are reserved
development services, not dependencies of any current request. No ORM, authentication,
queue, model runtime, or unused service/repository abstraction is introduced.

## Shared boundaries

`packages/contracts` owns protocol documentation. Backend producer tests and web
consumer tests enforce the small health contract; update both with protocol changes.
There is no generated schema, OpenAPI endpoint, or client library yet. Code generation
is deferred until a meaningful non-health API needs it.

The independent `packages/guardian-core` Java 8-compatible library owns mathematical
primitives and observation contracts. It has no runtime dependencies and no Spring
parent. Its build runs on JDK 21. See [core contracts](guardian-core.md).
Other shared directories reserve orchestration ownership and contain no executable domain code.
Future domain logic must remain independent of Spring, Next.js, and UI frameworks.
No app may import another app's source code. Shared distribution and language
choices will follow concrete runtime requirements.

Future safety-critical behavior needs a separate design preserving offline operation,
bounded latency, explicit uncertainty, deterministic calculations where appropriate,
and safe failure handling. It must not depend on an LLM/VLM. This foundation does
not implement or claim any such capability.

## Health and security

`GET /health/live` confirms process responsiveness. `GET /health/ready` confirms
readiness for stateless routes only. Add bounded dependency checks and HTTP 503
when future routes actually require adapters. Health output contains no credentials
or internal exception details.

Web `/health` is a human-readable page, not a machine readiness probe. It may return
HTTP 200 while showing API unavailable, and performs one fresh request per render.

Development services bind to loopback. Compose requires developer-supplied PostgreSQL
and MinIO credentials; Redis is unauthenticated and local-only. No permissive CORS,
debug error responses, or development hot-reload dependency is enabled in the API.
Before deployment, design authentication, TLS, secret management, backups, retention,
migrations, and observability. Compose is not a production specification.

## Build decisions

- npm workspaces manage the web and root tasks. A small Node launcher invokes the
  Maven wrapper on Windows and Unix without another task-runner framework.
- Spring Boot 4.1.1 manages backend dependency versions. Maven 3.9.16 is pinned;
  Java 21 compiles with lint warnings treated as errors. Spotless checks formatting,
  SpotBugs checks bytecode, and JUnit tests HTTP contracts before release packaging.
- Web uses ESLint, strict TypeScript, Vitest, and Prettier; production builds verify
  Next.js integration. Node 22.21.0 is the tested minimum, with npm 10.
- ESLint 9.39.5 matches the declared peer ranges of Next.js 16.4's React and
  accessibility plugins. npm marks ESLint 9 deprecated; migrate when those plugins
  support ESLint 10. No peer overrides or forced installs are used.
- Vitest 5 replaces the vulnerable earlier test-tool chain. npm still reports an
  unpatched `braces` denial-of-service advisory through Next's development lint
  dependencies. Review upstream fixes; do not downgrade Next.js or suppress audits.
  The exact development-only exception and its enforced limits are recorded in
  [security notes](security.md). This is not a vulnerability-free dependency claim.
- CI independently checks backend, web, and Compose configuration without deployment
  credentials. Runtime infrastructure verification is separate from static checks.
  Backend CI also runs the production web/API smoke test. Local `npm run verify`
  performs all application readiness checks without Docker or data services.
  It also runs a clean Guardian core build, tests and static analysis.

## Future critical local loop

```text
Camera / IMU -> Sensor synchronization -> Perception -> Ego-motion compensation
 -> World Model -> Physics / Geometry -> Trajectory -> Risk -> Attention
 -> Audio/Haptics
```

This is the intended on-device flow, not an implemented pipeline. Task 002 implements
only mathematical utilities and immutable contracts. Critical hazard decisions must
never require Spring Boot, a network or an LLM. Web and Spring Boot belong to the
separate cloud/explore and control-plane loop; optional cloud work must not block
local decisions. See [ADR 0002](adr/0002-on-device-guardian.md) and the
[R&D roadmap](research/GUARDIAN_RND_ROADMAP.md).

## Calibration-driven geometry

Task 003 extends guardian-core with camera projection/distortion, image transforms
and nominal world-ray/ground intersections. It retains zero runtime dependencies,
Java 8 compatibility, immutable inputs and explicit frame/time identities.
Web and Spring Boot remain independent of this library. Serialization and hardware
adapters stay outside it. See [ADR 0003](adr/0003-calibration-driven-camera-geometry.md)
and [camera model](geometry/CAMERA_MODEL.md). Task 006 adds optional Python detector
adapters outside the core. Task007 adds prototype image tracking and Task008 adds
model-independent depth sampling; no safety policy has been implemented.

## Temporal and motion foundation

Task 004 extends guardian-core with clock-explicit bounded histories, temporal
alignment, IMU nominal mathematics, configurable filters, derivatives and prediction.
Immutable observations/results can be shared; mutable processing instances are
single-owner and expose reset. There are no internal threads or clocks. This does
not implement inertial navigation, tracking or safety policy. See
[sensor fusion architecture](motion/SENSOR_FUSION_ARCHITECTURE.md).
