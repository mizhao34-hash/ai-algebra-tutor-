# Deployment

Backend: Docker on Render (`render.yaml`, `backend/Dockerfile`). Frontend: Vercel.

Live (deployed 2026-11-14):
- Site: https://ai-algebra-tutor-pi.vercel.app
- API: https://algebra-tutor-api.onrender.com (`/health`, `/docs`)
- Repo: github.com/mizhao34-hash/ai-algebra-tutor- (private). Pushing to `main` redeploys both.
- Before a demo, open `/health` ~1 min early: the free Render service sleeps when idle.

## 1. Push the repo to GitHub
Create an empty **private** repo on github.com, then:
```
git remote add origin https://github.com/<you>/ai-algebra-tutor.git
git push -u origin main
```
`.env` (API key), raw data and train/val/test CSVs are gitignored and never pushed.

## 2. Backend on Render
1. render.com → **New → Blueprint** → pick the repo. It reads `render.yaml`.
2. When asked, set `ANTHROPIC_API_KEY` (your key) and leave `ALLOWED_ORIGINS` for step 4.
3. Wait for the build, then open `https://<service>.onrender.com/health` → `{"ok":true}`.

Free plan caveats: the service sleeps after ~15 min idle (first request then takes
~1 min), and the SQLite file in /tmp is wiped on restart/redeploy.

## 3. Frontend on Vercel
1. vercel.com → **Add New → Project** → import the repo.
2. **Root Directory**: `frontend`.
3. **Environment Variable**: `NEXT_PUBLIC_API_URL` = the Render URL (no trailing slash).
4. Deploy, and note the Vercel URL.

## 4. Connect them
In Render → the service → Environment, set `ALLOWED_ORIGINS` = the Vercel URL
(e.g. `https://ai-algebra-tutor.vercel.app`) and save (Render redeploys).

## Local Docker check (optional)
```
docker build -f backend/Dockerfile -t algebra-tutor-api .
docker run --rm -p 8000:8000 --env-file .env algebra-tutor-api
```
