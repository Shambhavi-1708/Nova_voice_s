"""
server.py

Single production backend for NovaVoice. Replaces the old two-terminal
setup (api_server.py + `python -m http.server`) with one process that:

  1. Serves the frontend (index.html)
  2. Exposes the calendar + personalities REST API
  3. Relays the Gemini Live WebSocket connection

Point 3 is the important security piece: the Gemini API key lives only in
this server's environment. The browser connects to *this server's*
WebSocket endpoint, which opens its own authenticated connection to Gemini
and transparently pipes messages both ways — so the key is never sent to,
or visible from, the browser.

Run locally:
    uvicorn server:app --reload --port 8000

Run in production (e.g. on Render):
    uvicorn server:app --host 0.0.0.0 --port $PORT
"""

import os
import asyncio
from pathlib import Path

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from calendar_tool import book_meeting, check_availability
from personalities import list_personalities, DEFAULT_PERSONALITY

load_dotenv()

BASE_DIR = Path(__file__).parent
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_WS_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
    f"?key={GEMINI_API_KEY}"
)

# ===== Basic abuse protection =====
# Public deployments have no per-visitor login, so these limits stop a
# script (accidental or malicious) from spamming real calendar bookings or
# burning through Gemini quota via repeated relay connections.
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="NovaVoice")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Too many requests — please slow down."})


@app.get("/")
async def index():
    """Serves the frontend."""
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/personalities")
async def get_personalities():
    """Returns all available AI personalities and the default, for the frontend dropdown/tabs."""
    return {"personalities": list_personalities(), "default": DEFAULT_PERSONALITY}


@app.post("/api/check_availability")
@limiter.limit("20/minute")
async def api_check_availability(request: Request):
    data = await request.json()
    print(f"\n📅 [API REQUEST] Checking availability for {data.get('date')}")
    result = check_availability(date_iso=data.get('date'))
    print(f"✅ [API RESPONSE] {result}")
    return {"result": result}


@app.post("/api/book_meeting")
@limiter.limit("5/minute")
async def api_book_meeting(request: Request):
    data = await request.json()
    print(f"\n🔔 [API REQUEST] Booking {data.get('title')} at {data.get('date_time')}")
    result = book_meeting(date_time_iso=data.get('date_time'), name=data.get('guest_email'))
    print(f"✅ [API RESPONSE] {result}")
    return {"result": result}


@app.websocket("/ws/gemini")
async def gemini_relay(client_ws: WebSocket):
    """
    Transparent bidirectional relay between the browser and Gemini Live.
    Every message the browser sends (setup, audio chunks, tool responses)
    is forwarded to Gemini untouched, and every message Gemini sends back
    is forwarded to the browser untouched — this endpoint never inspects
    or modifies the protocol, it just keeps the API key out of the client.
    """
    await client_ws.accept()

    if not GEMINI_API_KEY:
        await client_ws.close(code=1011, reason="Server is missing GEMINI_API_KEY")
        return

    try:
        async with websockets.connect(GEMINI_WS_URL, max_size=None) as gemini_ws:

            async def browser_to_gemini():
                try:
                    while True:
                        msg = await client_ws.receive_text()
                        await gemini_ws.send(msg)
                except WebSocketDisconnect:
                    pass

            async def gemini_to_browser():
                try:
                    async for msg in gemini_ws:
                        text = msg if isinstance(msg, str) else msg.decode("utf-8")
                        await client_ws.send_text(text)
                except websockets.exceptions.ConnectionClosed:
                    pass

            # Run both directions concurrently until either side disconnects
            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except Exception as e:
        print(f"❌ GEMINI RELAY ERROR: {e}")
    finally:
        try:
            await client_ws.close()
        except Exception:
            pass


if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
