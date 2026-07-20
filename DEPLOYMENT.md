# Deploying NovaVoice publicly (Render)

This turns your local project into a real public URL, with your Gemini key
kept safely on the server and real Google Calendar booking working for
anyone who visits. Follow these in order — steps 1–3 only need doing once.

---

## 0. What changed from your local setup

- **`server.py`** replaces `api_server.py`. It's one FastAPI process that
  serves the frontend, the calendar API, *and* a WebSocket relay to Gemini
  — so you only ever run **one** command/server now, not two.
- **`index.html`** no longer asks for a Gemini API key. It connects to your
  own server's `/ws/gemini` relay instead, which holds the real key.
- **`calendar_tool.py`** can now load credentials from an environment
  variable (`GOOGLE_TOKEN_JSON`) instead of only a local `token.json` file
  — needed because most hosts wipe local files on every redeploy.
- **`requirements.txt`** has 3 new packages: `fastapi`, `uvicorn`, `slowapi`.

Locally, running it is now just:
```powershell
uvicorn server:app --reload --port 8000
```
Then open `http://localhost:8000` — no key entry, calendar still works
using your existing `token.json`. Test this locally first before deploying.

---

## 1. Get a dedicated Gemini API key for the server

Go to [Google AI Studio](https://aistudio.google.com/apikey) → **Create API
key**. This is the key that will live on your server and be shared by every
visitor — so it's worth keeping an eye on its usage/quota in AI Studio
after you post the link publicly.

---

## 2. Publish your Google OAuth app (important — prevents silent breakage)

While your OAuth consent screen is in **Testing** status, Google expires
refresh tokens after **7 days** — which would silently break calendar
booking on your live site a week after deploying.

1. [Google Cloud Console](https://console.cloud.google.com/) → **APIs &
   Services → Google Auth Platform → Audience**.
2. Click **Publish App**.
3. Confirm. Your app stays unverified (fine — only you ever see the
   "Google hasn't verified this app" screen, since visitors never go
   through OAuth themselves, they only talk to your already-authorized
   calendar).

---

## 3. Get your token as a single environment variable

1. Locally, open `token.json` in VS Code.
2. Select all, copy the entire contents (it's one line of JSON).
3. Keep it handy — you'll paste it into Render's environment variables in
   step 5 as `GOOGLE_TOKEN_JSON`.

---

## 4. Push your project to GitHub

If you haven't already:
```powershell
git init
git add .
git commit -m "NovaVoice"
```
Create a new repo on [github.com/new](https://github.com/new) (private is
fine), then follow GitHub's shown commands to push, e.g.:
```powershell
git remote add origin https://github.com/yourname/novavoice.git
git branch -M main
git push -u origin main
```

**Before committing**, make sure `.gitignore` includes `.env` and
`token.json` (it already does in this project) so you never push real
secrets to GitHub.

---

## 5. Deploy on Render

1. Go to [render.com](https://render.com) → sign up/log in (GitHub login is
   easiest) → **New → Web Service**.
2. Connect the GitHub repo you just pushed.
3. Configure:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add each of these (values from your own
   `.env` / Google Cloud):
   | Key | Value |
   |---|---|
   | `GEMINI_API_KEY` | the key from step 1 |
   | `GOOGLE_CLIENT_ID` | from your `.env` |
   | `GOOGLE_CLIENT_SECRET` | from your `.env` |
   | `HOST_CALENDAR_ID` | your Gmail |
   | `HOST_EMAIL` | your Gmail |
   | `GOOGLE_TOKEN_JSON` | the full token.json contents from step 3 |
5. Click **Create Web Service**. Render will build and deploy — takes a
   couple of minutes on the first run.
6. You'll get a public URL like:
   ```
   https://novavoice-xxxx.onrender.com
   ```
   **This is your link for LinkedIn.**

---

## 6. Test it for real

1. Open the Render URL in a normal (not incognito) browser window.
2. Click **Enter NovaVoice**, tap the mic, try:
   > "Check if my calendar is free tomorrow, and if so, book a 30-minute
   > demo, my email is you@example.com."
3. Confirm the event actually appears on your real Google Calendar.
4. Try switching a personality tab too.

---

## Notes worth knowing

- **Free tier sleeps.** Render's free web services spin down after ~15
  minutes of no traffic and take 20–50 seconds to wake up on the next
  visit. Fine for a LinkedIn demo link people click occasionally; if you
  want it always-instant, Render's cheapest paid tier removes the sleep.
- **Rate limits are on by default** (`server.py` limits calendar checks to
  20/min and bookings to 5/min per visitor IP) to stop your calendar or
  Gemini quota from being spammed by bots or repeat clicks.
- **Every booking goes on your real calendar.** Since this uses your
  personal Google account (not per-visitor OAuth), anyone who uses the demo
  is booking a real 30-minute slot with you. Worth deleting test bookings
  afterward, and maybe mentioning in your LinkedIn post that it's a live
  demo booking real time on your calendar (a nice touch, honestly — it
  proves the feature is real).
