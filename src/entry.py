import json
from js import Response
from urllib.parse import urlparse, parse_qs

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

async def on_fetch(request, env):
    url_str = str(request.url)
    method = str(request.method)

    # Handle CORS Preflight
    if method == "OPTIONS":
        return Response.new("", headers=CORS_HEADERS)

    # Ingestion Route (Home Assistant -> Cloudflare)
    if method == "POST" and "/update" in url_str:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {env.SECRET_TOKEN}":
            return Response.new(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers={"Content-Type": "application/json"}
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
                headers={"Content-Type": "application/json"}
            )
        except Exception as err:
            return Response.new(
                json.dumps({"error": str(err)}),
                status=400,
                headers={"Content-Type": "application/json"}
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
            headers={"Content-Type": "application/json", **CORS_HEADERS}
        )

    return Response.new("Not Found", status=404)
