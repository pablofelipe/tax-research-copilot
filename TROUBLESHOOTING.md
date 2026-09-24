# Troubleshooting

Real issues encountered while developing and running this project locally, with what actually resolved them.

## Docker Desktop update fails with a conflicting-instance error

**Symptom**: updating Docker Desktop (via the in-app updater or `winget upgrade --id Docker.DockerDesktop`) fails, sometimes with an installer exit code around `4294967290`, or a UAC/elevation-related failure when run non-interactively.

**Cause**: a previous update attempt (often the in-app updater appearing "stuck") leaves orphaned `Docker Desktop.exe`, `com.docker.backend.exe`, and installer processes running. A second install attempt then conflicts with the first.

**Fix**: close Docker Desktop from the system tray ("Quit Docker Desktop"), then check for remaining processes and end them from an **elevated** PowerShell (regular processes reject `taskkill` from a non-admin shell):

```powershell
Stop-Process -Name "Docker Desktop Installer" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "com.docker.backend" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "com.docker.build" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
```

If `winget upgrade` itself is run from a non-elevated shell, the installer's UAC prompt can never be answered and the upgrade fails with exit code 1. Run `winget upgrade --id Docker.DockerDesktop` from an elevated PowerShell directly, without `--silent`, so you can see and approve the prompt.

## Docker Desktop shows "Starting the Docker Engine..." indefinitely, or WSL throws an unhandled exception

**Symptom**: `wsl --unregister docker-desktop` (run internally by Docker Desktop) fails with `Wsl/Service/ERROR_UNHANDLED_EXCEPTION`; afterward the VM shuts down and Docker Desktop never finishes starting.

**Fix**: update WSL itself, then restart it:

```powershell
wsl --update
wsl --shutdown
```

Reopen Docker Desktop afterward. If the VM still shows a graceful shutdown with no restart in `%LOCALAPPDATA%\Docker\log\vm\init.log` and the engine never comes back, a full machine reboot resolves the remaining inconsistent WSL state — this does not lose any data in named Docker volumes.

## `docker compose up -d` recreates empty volumes after a Docker Desktop update

**Symptom**: after updating Docker Desktop, previously ingested data (the `source_documents` row, pulled Ollama models) is gone, even though the named volumes (`postgres_data`, `ollama_data`) still exist.

**Cause**: a Docker Desktop update/reinstall can reset the underlying WSL2 data disk that backs those volumes. `docker volume inspect` on the affected volumes shows a `CreatedAt` timestamp from just now, not from when the data was originally written — that is the sign the volume was recreated empty, not preserved.

**Fix**: there is no data recovery from this — reingest the real source document(s) via `go run ./cmd/ingest ...` and re-pull the Ollama models (`ollama pull llama3.1:8b`, `ollama pull nomic-embed-text`). Nothing here is fabricated data; it is re-derived from the same real, public sources.

## `ollama pull` succeeds for the chat model but `/api/embed` returns 404 with "model not found"

**Symptom**: `OllamaEmbeddingClient.embed()` (or a direct `curl` to `/api/embed`) fails even though `ollama list` shows the chat model present.

**Cause**: `nomic-embed-text` (the embedding model) is a separate pull from `llama3.1:8b` (the chat model) — pulling one does not pull the other.

**Fix**:

```bash
docker exec tax-research-copilot-ollama-1 ollama pull nomic-embed-text
```

## A graph run times out with `httpx.ReadTimeout` or `httpcore.ReadTimeout`

**Symptom**: `app.main`/`app.evaluate` fails partway through a run (often at the `research` or `critique` node) with a read timeout.

**Cause**: Llama 3.1 8B on CPU-only inference (no GPU passthrough — see [ADR-0001](docs/adr/0001-langgraph-orchestration-for-multi-step-tax-research.md), LLM Provider amendment) can take minutes per call, especially with a large retrieved context. The default `httpx.Client` timeout is too short for this.

**Fix**: this project's `OllamaClient`/`OllamaEmbeddingClient` are already configured with a 600-second timeout in `app/main.py` and `app/evaluate.py`. If you see this error, check that you're using those entry points (not a custom script with a shorter default timeout), and budget real wall-clock time — a single question can take on the order of 10 minutes end to end.

## The evaluation suite (`app.evaluate`) is too slow to run in full

**Symptom**: running the full 21-question dataset (or even `--limit 2`) takes far longer than expected.

**Cause**: this is expected, not a bug — a single case takes roughly 609 seconds on CPU-only inference, so the full dataset is on the order of three and a half hours (see [ADR-0001](docs/adr/0001-langgraph-orchestration-for-multi-step-tax-research.md)'s Known Limitation amendment). This is also why CI does not run the real evaluation harness ([ADR-0006](docs/adr/0006-ci-scope.md)).

**Fix**: use `--limit 1` (or a small number) for a smoke check. There is currently no faster path with the local, zero-cost model.

## `CriticError: critic LLM conflict group is invalid`

**Symptom**: a graph run fails with `CriticError` during the `critique` node, naming a conflict group with fewer than two sub-answer indices.

**Cause**: this is Llama 3.1 8B's own unreliability at the conflict-detection task, not an application bug — documented as a known limitation in [ADR-0001](docs/adr/0001-langgraph-orchestration-for-multi-step-tax-research.md). The system is correctly refusing to accept a malformed "conflict" rather than silently producing a wrong `DisputedPosition`.

**Fix**: none for v1 — this is the intended failure mode (a loud, typed error instead of a silently wrong answer). Retry the question, or see the ADR's Known Limitation section for the deferred fix options being tracked.

## `Deserializing unregistered type ... from checkpoint` warning

**Symptom**: `app.main`/`app.evaluate` prints a warning like `Deserializing unregistered type app.core.schemas.SubAnswer from checkpoint. This will be blocked in a future version.`

**Cause**: LangGraph's checkpoint serialization does not have `SubAnswer`/`DisputedPosition` explicitly registered as allowed types for its msgpack-based checkpoint format.

**Fix**: this is a warning, not an error — the run completes correctly. It is not yet addressed in this project; if LangGraph enforces `LANGGRAPH_STRICT_MSGPACK=true` by default in a future version, these Pydantic models will need to be added to `allowed_msgpack_modules` at graph-build time.
