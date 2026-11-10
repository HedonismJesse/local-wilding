from otari_client import OtariClient

r = OtariClient().models()
data = r.body.get("data") or []
for m in data:
    p = m.get("pricing") or {}
    params = m.get("supported_parameters") or []
    print(
        f"{m['id']:50s} in={p.get('input_price_per_million','?'):>10} "
        f"out={p.get('output_price_per_million','?'):>10} tools={'tools' in params}"
    )
