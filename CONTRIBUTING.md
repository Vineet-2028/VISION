# Contributing

1. Follow the root README to install Node 22, npm 10, and JDK 21 dependencies.
2. Create a focused branch (`codex/` is the default for agent-created branches).
3. Keep application code in its application and shared domain logic in its owned
   package. Do not add cross-application source imports.
4. Use strict TypeScript and typed Java. Do not suppress checks to make a
   build pass. Add behavioral tests for changes to contracts, failure handling,
   or domain logic.
5. Run `npm run format`, `npm run format:api`, `npm run format:core`, and `npm run verify`. Java checks
   include formatting, compiler lint, SpotBugs, JUnit, and JAR packaging. The API
   produces an executable JAR; Guardian core produces an independent library JAR.
6. Include the problem, resulting behavior, checks run, and remaining limitations
   in the pull request. Update architecture decisions when boundaries change.

Commit the npm lockfile, pinned Maven versions, and Maven wrapper. Never commit `.env` files,
build output, credentials, datasets, model weights, or captured
sensor data. `.env.example` files document names and safe defaults only.

The foundation deliberately contains no perception models or active Guardian
lifecycle. Model work requires a separate design covering consent, evaluation,
latency, failure handling, data retention, and deployment. New dependencies must
solve a concrete requirement; avoid framework layers around placeholders.

## Perception laboratory contributions

Use the isolated environment and pinned dependencies in
[the lab setup guide](apps/perception-lab/README.md). Run `npm run format:lab`,
`npm run check:lab` and the full `npm run verify`. Keep source timestamps and
processing clocks separate, bound retained buffers, preserve core ImageTransform
geometry, and test cancellation/failure cleanup. Never commit real media, benchmark
artifacts or identifying metadata. No perception code belongs in the web/API.
