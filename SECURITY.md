# Security Policy

## Project status

This project is in early, active development and has no hosted deployment — it runs locally, against local infrastructure (PostgreSQL, Ollama), via the instructions in the [README](README.md). There is no production environment, no user data collection, and no publicly reachable endpoint. The threat model is accordingly narrower than a deployed service: the concerns that matter here are dependency vulnerabilities, unsafe handling of fetched external content (the Go ingestion service parses HTML from government sources), and injection risks in code that builds SQL or shells out to external binaries (`curl`, via `CurlFetcher`).

## Known, accepted risk in local configuration

`docker-compose.yml` uses a hardcoded development-only PostgreSQL user and password (`tax_research` / `tax_research`). This is intentional for local development and is **not safe to use as-is in any environment reachable from outside your own machine**. If you adapt this project to run anywhere else, replace those credentials first.

## Reporting a vulnerability

If you find a security issue in this repository (a real vulnerability — e.g., a SQL injection path, an unsafe deserialization, a command-injection risk in the fetch/parse pipeline), please report it privately rather than opening a public issue:

- Preferred: use GitHub's [private vulnerability reporting](../../security/advisories/new) for this repository.
- Alternative: email pablofelipe@gmail.com with a description and, if possible, steps to reproduce.

Please do not open a public GitHub issue for a security report until it has been triaged.

## Response

This is a single-maintainer project without a formal SLA. Reports will be acknowledged and investigated as promptly as possible; there is no guaranteed response time.
