# Deployment

How the hosted demo environment is set up and operated. See [ADR-0007](adr/0007-hosted-demo-deployment.md) for why each of these choices was made; this document is the operational how-to.

## Prerequisites

- An Oracle Cloud Infrastructure (OCI) account with the Always Free tier available.
- A domain or subdomain you control, with its DNS managed somewhere you can add an `A` record (a free option such as [DuckDNS](https://www.duckdns.org/) works — Let's Encrypt only needs a publicly resolvable name, not a paid registrar).
- A [Groq](https://console.groq.com/) API key.

## 1. Create the compute instance

In the OCI console: **Compute → Instances → Create Instance**.

- **Image**: Ubuntu (latest LTS).
- **Shape**: `VM.Standard.A1.Flex` (the Ampere ARM shape covered by the Always Free allocation) — the free allocation is up to 2 OCPUs / 12 GB RAM total. If creation fails with an "out of host capacity" error, try a different availability domain, a smaller OCPU/memory request, or simply retry later — this is a known, common constraint on this shape, not specific to this project.
- **Networking**: use the default VCN, or create one. Note the instance's public IP once it's running.
- **SSH keys**: generate or upload a key pair — you'll need it to connect.

By default, OCI's security list only allows inbound SSH (port 22). Add ingress rules for **80/tcp** and **443/tcp** (Networking → Virtual Cloud Networks → your VCN → Security Lists → Default Security List → Add Ingress Rules), otherwise Caddy can never obtain a certificate or serve traffic.

## 2. Point a domain at the instance

Create an `A` record for your chosen domain/subdomain pointing at the instance's public IP. Confirm it resolves before continuing:

```bash
dig +short your-domain.example
```

## 3. Install Docker on the instance

```bash
ssh ubuntu@<instance-ip>
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# log out and back in for the group change to apply
```

## 4. Deploy the stack

```bash
git clone <this repository> tax-research-copilot
cd tax-research-copilot

cat > .env <<EOF
DOMAIN=your-domain.example
GROQ_API_KEY=<your Groq API key>
EOF

docker compose -f docker-compose.yml -f docker-compose.hosted.yml up -d postgres ollama jaeger api caddy
docker exec tax-research-copilot-ollama-1 ollama pull nomic-embed-text
```

Only `nomic-embed-text` needs to be pulled — the chat model runs on Groq in this environment (`LLM_PROVIDER=groq`, set in `docker-compose.hosted.yml`), not through local Ollama.

The ingestion CLI still runs the same way it does locally (`docker compose run --rm ingestion ...`) to populate `source_documents`, pointed at this instance's Postgres.

## 5. Generate the demo credential

```bash
./deploy/rotate-credential.sh
```

This prints a username and password. Hand it out manually, on request — nothing here emails or publishes it automatically. Re-run the same script any time to rotate it; Caddy reloads with the new credential.

## 6. Verify

```bash
curl -u <username>:<password> -X POST https://your-domain.example/ask \
  -H 'content-type: application/json' \
  -d '{"query": "..."}'
```

A `401` means the credential is wrong or Caddy hasn't picked up the latest one; a certificate error usually means DNS hasn't propagated yet, or ports 80/443 aren't open in the OCI security list.

## Operational notes

- **Restarting after a host reboot**: every service in both compose files has `restart: unless-stopped` where it matters (`api`, `caddy`) or is part of the always-running base stack — a `docker compose up -d` after a reboot brings everything back without re-running the credential script.
- **OCI idle reclamation**: Oracle can reclaim an Always Free A1 instance if, over a 7-day window, its 95th-percentile CPU utilization, network utilization, and memory utilization are all below 20%. There is no automated monitoring for this yet (tracked as an open question in ADR-0007) — if the demo link stops responding, check whether the instance still exists in the OCI console before debugging anything else.
- **Updating the deployed code**: `git pull`, then `docker compose -f docker-compose.yml -f docker-compose.hosted.yml up -d --build api`.

## Migrating off a trial-funded instance

`VM.Standard.A1.Flex` (Ampere) is frequently out of free capacity at instance-creation time in a given availability domain. If the Always Free shape isn't available when you first set this up, it's reasonable to provision a paid shape temporarily (covered by the 30-day/$300 free trial credit, not a real charge) to make progress, and migrate once free capacity frees up:

1. Keep retrying instance creation with `VM.Standard.A1.Flex` (up to 2 OCPUs / 12 GB under Always Free) periodically — no cost to attempt, and capacity availability fluctuates.
2. Once it succeeds, repeat steps 3–5 above on the new instance (Docker, deploy, credential rotation) — everything here is shape-independent.
3. Update the domain's `A` record to the new instance's public IP.
4. Terminate the old instance.

Do this **before the trial ends** (30 days from account creation, or sooner if the $300 credit is exhausted) — after that, Oracle reclaims any non-Always-Free resource automatically, taking the demo down without warning.
