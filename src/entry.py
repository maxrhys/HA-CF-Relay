import json
from js import Response, Headers
from urllib.parse import urlparse, parse_qs

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

def make_headers(extra=None):
    h = Headers.new()
    for k, v in CORS_HEADERS.items():
        h.set(str(k), str(v))
    if extra:
        for k, v in extra.items():
            h.set(str(k), str(v))
    return h

async def on_fetch(request, env):
    url_str = str(request.url)
    method = str(request.method)

    # Handle CORS Preflight
    if method == "OPTIONS":
        return Response.new("", status=204, headers=make_headers())

    # Ingestion Route (Home Assistant -> Cloudflare)
    if method == "POST" and "/update" in url_str:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {env.SECRET_TOKEN}":
            return Response.new(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers=make_headers({"Content-Type": "application/json"})
            )

        try:
            payload = json.loads(await request.text())
            raw_cache = await env.SENSOR_KV.get("telemetry_store")
            store = json.loads(raw_cache) if raw_cache else {}

            # Merge incoming device dicts into existing cache
            for device_id, device_data in payload.items():
                store[device_id] = device_data

            await env.SENSOR_KV.put("telemetry_store", json.dumps(store))
            return Response.new(
                json.dumps({"status": "ok"}),
                status=200,
                headers=make_headers({"Content-Type": "application/json"})
            )
        except Exception as err:
            return Response.new(
                json.dumps({"error": str(err)}),
                status=400,
                headers=make_headers({"Content-Type": "application/json"})
            )

    # Public Consumption Route (Web Client -> Cloudflare)
    if method == "GET" and "/data" in url_str:
        raw_cache = await env.SENSOR_KV.get("telemetry_store")
        store = json.loads(raw_cache) if raw_cache else {}

        parsed_url = urlparse(url_str)
        params = parse_qs(parsed_url.query)
        device_filter = params.get("device", [None])[0]

        if device_filter:
            output = store.get(device_filter, {"error": "Device not found"})
        else:
            output = store

        return Response.new(
            json.dumps(output),
            status=200,
            headers=make_headers({"Content-Type": "application/json"})
        )

    return Response.new("Not Found", status=404, headers=make_headers())
