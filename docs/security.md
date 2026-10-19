# Foundation security review

The local web/API foundation has no authentication, user data, or active Guardian.
Production deployment needs a separate review of its network, TLS, authentication,
secret storage, monitoring, and recovery configuration.

## Reviewed development dependency advisory

`GHSA-vfj7-8cjw-p6xm` affects `braces` through Next.js ESLint tooling. npm reports
five high-severity dependency entries for this one underlying advisory. No patched
release is available as of 2026-10-12. This finding is not fixed or suppressed.

Repository-specific exposure is limited: this chain is development-only, and the
Next plugin invokes its glob expansion only when `settings.next.rootDir` is set.
Our ESLint configuration does not set it. HTTP requests cannot supply these patterns.
Changing lint configuration already requires permission to execute repository code.

`npm run security` permits only this exact advisory in the five reviewed development
packages at the reviewed lockfile versions, checks that rootDir glob expansion remains disabled, and fails on unknown
advisories, production-package findings, or audit-service errors. Reassess this decision
when changing lint configuration or dependencies. Upgrade promptly when a compatible
fix exists. Never use forced downgrades or disable lint rules to obtain a green audit.

This bounded tooling risk does not block local feature development. It is not a
claim that the dependency is vulnerability-free. Java dependencies and deployment
images require their own vulnerability review before production release.

Next.js telemetry is disabled by the checked-in CLI launcher. Do not log credentials,
sensor data, or environment values. Examples contain no real secrets.
