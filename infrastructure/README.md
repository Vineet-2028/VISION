# Development infrastructure

The root `compose.yaml` provisions PostgreSQL, Redis, and MinIO with health checks,
versioned image tags, loopback ports, and persistent named volumes. It starts no
application containers. Start with `npm run infra:up` after filling
the root `.env` from its example. Compose fails early for missing credentials.

The MinIO console is at <http://localhost:9001>; its S3 endpoint is port 9000.
Buckets are not created automatically because the API has no storage consumer.
Similarly, no database schema or Redis key protocol exists yet.

PostgreSQL's `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` initialize an
empty data volume only. Editing `.env` does not rotate credentials or recreate a
database in an existing volume. Change existing roles through PostgreSQL's
administrative tools; preserve the volume and its data.

`npm run infra:down` preserves data. Deleting volumes is an explicit destructive developer
operation, never part of setup or routine shutdown. Do not reuse this configuration
for production: TLS, Redis authentication, credential rotation, network isolation,
resource budgets, monitoring, backups, and restore tests require deployment design.
