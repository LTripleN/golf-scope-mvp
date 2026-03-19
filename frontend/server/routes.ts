import type { Express } from "express";
import { createServer, type Server } from "http";
import multer from "multer";

// FastAPI backend URL — defaults to localhost for dev, override via env for prod
const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10 MB
});

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // POST /api/analyze — proxy multipart upload to FastAPI backend
  app.post("/api/analyze", upload.single("file"), async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: "No video file uploaded." });
      }

      // Build a native Web FormData (works with Node fetch/undici)
      const form = new FormData();
      const blob = new Blob([req.file.buffer], {
        type: req.file.mimetype || "video/mp4",
      });
      form.append("file", blob, req.file.originalname || "upload.mp4");

      // Handedness is now optional — backend auto-detects if not provided
      const handedness = req.body.handedness;
      if (handedness && ["right", "left"].includes(handedness)) {
        form.append("handedness", handedness);
      }

      const response = await fetch(`${FASTAPI_URL}/analyze`, {
        method: "POST",
        body: form,
      });

      const data = await response.json();

      if (!response.ok) {
        return res.status(response.status).json(data);
      }

      return res.json(data);
    } catch (err: any) {
      console.error("Analysis proxy error:", err);
      return res.status(502).json({
        error:
          "Could not reach the analysis engine. Please try again in a moment.",
      });
    }
  });

  return httpServer;
}
