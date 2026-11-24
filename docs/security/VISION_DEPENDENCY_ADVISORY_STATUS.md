# Alpha V1.1 dependency advisory — 2026-11-18

Status: **SECURITY_BLOCKER_EXTERNAL_UNRESOLVED**. No audit exception,
lockfile falsification, forced downgrade, or unverified fork was adopted.

The [reviewed advisory](https://github.com/advisories/GHSA-fc5q-39xc-vjpf)
identifies CVE-2026-112366, repeated-extglob ReDoS in picomatch through 4.0.7,
with no patched version. The [upstream releases](https://github.com/micromatch/picomatch/releases)
and `npm view picomatch dist-tags --json` both identify 4.0.7 as latest.
The advisory-linked [open PR 194](https://github.com/micromatch/picomatch/pull/194)
addresses leading question-mark parsing; its author explicitly does not claim
a security fix. It is not an approved replacement for this advisory.

## Installed paths and reachability

Full graph: `benchmark-results/final-closure-dependency-paths.txt`.
Audit: `benchmark-results/final-closure-audit.json`: **16 high findings,
zero critical**, propagated from one picomatch advisory.

| Installed path beneath apps/web                                                                                    | Use and input ownership                                        |
| ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| eslint-config-next 16.4.6 → @next/eslint-plugin-next 16.4.6 → fast-glob 3.3.1 → micromatch 4.0.8 → picomatch 2.3.2 | Developer lint file patterns; not an application HTTP glob API |
| vitest 5.0.3 → picomatch 4.0.7                                                                                     | Test discovery/filtering                                       |
| vitest → tinyglobby 0.2.17 → picomatch 4.0.7                                                                       | Test file discovery                                            |
| vitest → tinyglobby → fdir 6.5.0 → picomatch 4.0.7                                                                 | Test directory traversal                                       |
| vitest → vite 8.3.4 → picomatch 4.0.7                                                                              | Test/build tooling                                             |

Repository application-source inspection found no direct picomatch/micromatch
imports or user-facing glob processing. This narrows observed reachability;
it does **not** prove non-exploitability of every transitive or bundled dependency.
Untrusted checkouts, configuration, plugins, and test patterns can reach developer
tooling. An application authenticated on loopback is not a substitute for patching.

## Remediation evaluated

1. Official patch: none published at this check.
2. Supported upgrade: latest eslint-config-next remains 16.4.6; latest Vitest
   5.1.0 still directly requires picomatch `^4.0.7` and tinyglobby. An upgrade
   therefore does not remove the vulnerable path.
3. Maintained alternative: minimatch is not an API-compatible replacement for
   all picomatch callers. Replacing the entire lint/test toolchain would require
   a separately validated migration; no verified compatible remediation exists here.
4. Dependency elimination: the affected paths support actual lint and unit tests.
   Removing those checks to obtain a clean audit is not acceptable.
5. Fork: none independently verified and approved. None installed.

Keep development strictly private, accept only trusted source/configuration,
bind Lab to loopback, require its secret and separate media consent, and keep real
captures outside synced folders. Do not expose development/test servers publicly.
The isolated browser QA installation in `.tools/browser-qa` is test tooling,
not an application dependency or a workaround for the main audit.

`npm run security` must continue failing until a legitimate fix passes the full
lockfile scan and compatibility checks. `--omit=dev` is not the release gate.
Public deployment and Alpha V1.1 promotion remain **NO**.
