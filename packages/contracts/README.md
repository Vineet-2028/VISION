# Contracts

This directory owns cross-application protocol documentation. No generated client
or schema library is necessary yet. The Spring Boot API implements the contract
below; no OpenAPI generation dependency is installed.

| Method | Path            | HTTP status | JSON                                       |
| ------ | --------------- | ----------- | ------------------------------------------ |
| GET    | `/health/live`  | 200         | `{"status":"ok","service":"sentinel-api"}` |
| GET    | `/health/ready` | 200         | `{"status":"ok","service":"sentinel-api"}` |

Readiness currently describes the stateless API, not the provisioned data services.
The web validates both fields, treats non-200 or malformed responses as unavailable,
and bounds the request to three seconds. Future dependency failures must return 503.
Update backend tests and web consumer tests together with protocol changes.
