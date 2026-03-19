# SwingAI — Golf Swing Analyzer

AI-powered golf swing analysis from face-on video. Upload a swing, get instant feedback on your setup, backswing, and impact positions.

## Features

- **Auto-detect handedness** — no manual input needed
- **9 swing metrics** across 3 phases (Setup, Backswing, Impact)
- **AI coaching summary** powered by Claude
- **Golfer-friendly UI** — color-coded insight cards, no jargon

## Architecture

```
golf-scope-mvp/
├── backend/          # FastAPI + MediaPipe Pose
│   ├── main.py       # API endpoint: POST /analyze
│   ├── video_processing.py  # ffmpeg frame extraction
│   ├── pose_metrics.py      # Pose detection + metric computation
│   ├── tips_engine.py       # Threshold-based rules engine
│   ├── coaching.py          # Claude AI coaching summary
│   └── requirements.txt
├── frontend/         # Vite + React + TypeScript + Tailwind
│   ├── client/       # React SPA
│   ├── server/       # Express proxy to FastAPI
│   └── shared/       # Shared types (schema.ts)
└── README.md
```

## Metrics Analyzed

| Metric | Phase | What It Measures |
|--------|-------|------------------|
| Spine Tilt | Setup | Side-to-side lean at address |
| Knee Flex | Setup | Bend in knees at setup |
| Stance Width | Setup | Feet spacing relative to shoulders |
| Backswing Sway | Backswing | Head lateral movement going back |
| Shoulder Turn | Backswing | Upper body rotation (projected width ratio) |
| Downswing Sway | Impact | Head movement through the ball |
| Hip Shift | Impact | Lateral hip bump toward target |
| Shoulder Tilt | Impact | Lead shoulder height vs trail |
| Posture Change | Impact | Spine angle consistency setup→impact |

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
# Download the MediaPipe model if not present:
# https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Express dev server runs on port 5000 and proxies `/api/analyze` to FastAPI on port 8000.

## Deploying to Render

### Backend (Web Service)

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Root directory:** `backend`
- **Environment:** Set `ANTHROPIC_API_KEY` for AI coaching

### Frontend (Static Site or Web Service)

- **Build command:** `npm install && npm run build`
- **Start command:** `NODE_ENV=production node dist/index.cjs`
- **Root directory:** `frontend`
- **Environment:** Set `FASTAPI_URL` to your backend's Render URL

## Tech Stack

- **Backend:** Python 3, FastAPI, MediaPipe Pose, OpenCV, ffmpeg-python
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **AI:** Anthropic Claude (coaching summaries)
