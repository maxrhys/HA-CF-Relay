# HA-CF-Relay (Cloudflare Worker)

Lightweight, secure edge telemetry broker built on **Cloudflare Workers** (Python runtime) and **Workers KV**.

It ingests sensor telemetry pushed from Home Assistant via authenticated `POST /update` and serves public reads via `GET /data` (with optional `?device=<id>`) without exposing your local network or Home Assistant instance.

> For the Home Assistant YAML integrations and Web Monitor dashboard, see the companion repository: [HA-CF-Relay-Client](https://github.com/maxrhys/HA-CF-Relay-Client).

---

## Architecture

```
[ Home Assistant (Local) ]
       │ (Outbound HTTPS POST via rest_command, every 5m)
       ▼
[ Cloudflare Worker: HA-CF-Relay (Python / Pyodide) ] ──► [ Workers KV Cache: SENSOR_KV ]
       ▲
       │ (Public HTTPS GET / CORS enabled)
[ Public Web Client ]
```

* **Ingestion Route (`POST /update`)**: Requires `Authorization: Bearer <SECRET_TOKEN>`. Merges arbitrary device dicts into a single KV document (`telemetry_store`) to ensure writes remain well within the 1,000 writes/day free tier (288 writes/day at 5-minute intervals).
* **Consumption Route (`GET /data`)**: Publicly accessible, CORS-enabled. Returns all devices or queries a single device via `?device=<id>`.

---

## Project Structure

```
.
├── wrangler.toml                 # Cloudflare Worker configuration & KV bindings
├── src/
│   └── entry.py                 # Python Worker entrypoint (Pyodide runtime)
├── .github/
│   └── workflows/
│       └── deploy.yml           # Automated GitHub Actions deployment via Wrangler
├── .gitignore
└── README.md
```

---

## Deployment & Setup

### 1. Log in to Cloudflare
```bash
npx wrangler login
```

### 2. Create the KV Namespace
```bash
npx wrangler kv namespace create SENSOR_KV
```
Copy the returned namespace `id` and paste it into `wrangler.toml`:
```toml
[[kv_namespaces]]
binding = "SENSOR_KV"
id = "PASTE_YOUR_KV_NAMESPACE_ID_HERE"
```

### 3. Set the Secret Token
```bash
npx wrangler secret put SECRET_TOKEN
```
Enter a secure random string (e.g. generated via `openssl rand -hex 24`).

### 4. Deploy
```bash
npx wrangler deploy
```
Note your assigned Worker URL: `https://ha-cf-relay.<YOUR_SUBDOMAIN>.workers.dev`.

---

## Continuous Deployment via GitHub

### Option A: Cloudflare Native Git Integration (Zero Secrets)
1. In Cloudflare Dashboard, navigate to **Workers & Pages > Create > Connect to Git**.
2. Select repository `maxrhys/HA-CF-Relay` and branch `main`.
3. Cloudflare will automatically build and deploy every commit pushed to `main`.

### Option B: GitHub Actions
1. In Cloudflare Dashboard, generate an API token with the **Edit Cloudflare Workers** template (**My Profile > API Tokens**).
2. In this GitHub repository, go to **Settings > Secrets and variables > Actions > New repository secret**.
3. Name: `CLOUDFLARE_API_TOKEN`, Value: Your Cloudflare API token.
4. Pushing changes to `src/` or `wrangler.toml` automatically deploys via [deploy.yml](.github/workflows/deploy.yml).
