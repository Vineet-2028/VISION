# Foundation security review

The November 5, 2026 npm audit found a pattern-amplification vulnerability in the
development-only TypeScript ESLint parser dependency. The root package override
selects minimatch 11.0.1 for that parser. Other consumers retain their compatible
versions. Remove the override when the parser declares a patched compatible version.
[Maintainer advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249).

After updating the lockfile, npm reported zero advisories. The security check now
fails on every reported advisory and on an incomplete audit response. The earlier
braces exception was retired. This result covers npm packages at the time of the
check. Java dependencies, Android dependencies and deployment infrastructure need
their own vulnerability review before release.

The local field gateway uses an ephemeral bearer token. Public deployment needs
a separate review of network exposure, TLS, identity, secret storage and recovery.

Next.js telemetry is disabled by the checked-in CLI launcher. Do not log credentials,
sensor data, or environment values. Examples contain no real secrets.
