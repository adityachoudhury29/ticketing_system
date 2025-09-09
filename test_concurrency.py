import asyncio, json, sys, time
import httpx

API_BASE = "http://127.0.0.1:8000"
EVENT_ID = 1
# mode: "contend" -> all requests same seat; "unique" -> different seats
MODE = "contend"
REQUESTS = 20
TOKEN = "YOUR_JWT_HERE"

async def book(client, payload, idx):
    try:
        r = await client.post(
            f"{API_BASE}/bookings",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10.0
        )
        return {
            "i": idx,
            "status": r.status_code,
            "body": r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        }
    except Exception as e:
        return {"i": idx, "status": "ERR", "body": str(e)}

async def main():
    seats = []
    if MODE == "contend":
        seats = [["A01-01"]] * REQUESTS
    else:
        seats = [[f"A01-{i:02d}"] for i in range(1, REQUESTS + 1)]

    async with httpx.AsyncClient() as client:
        start = time.perf_counter()
        tasks = [
            asyncio.create_task(
                book(client, {"event_id": EVENT_ID, "seat_identifiers": seat_list}, i)
            )
            for i, seat_list in enumerate(seats, 1)
        ]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

    success = sum(1 for r in results if r["status"] == 201)
    print(f"\nMode={MODE} total={REQUESTS} success={success} elapsed={elapsed:.3f}s\n")
    for r in results:
        print(f"[{r['i']:02d}] {r['status']} -> {r['body']}")

if __name__ == "__main__":
    asyncio.run(main())