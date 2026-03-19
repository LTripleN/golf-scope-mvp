import { z } from "zod";

// Structured insight from the backend
export const insightSchema = z.object({
  key: z.string(),
  label: z.string(),
  value: z.number(),
  unit: z.string(),
  status: z.enum(["good", "watch", "fix"]),
  description: z.string(),
  category: z.enum(["setup", "backswing", "impact"]),
});

export type Insight = z.infer<typeof insightSchema>;

// Response from the analysis endpoint
export const analysisResultSchema = z.object({
  scope: z.record(z.string(), z.number()),
  findings: z.array(z.string()),
  tips: z.array(z.string()),
  coaching_summary: z.string(),
  handedness: z.enum(["right", "left"]),
  handedness_source: z.enum(["auto", "user"]),
  insights: z.array(insightSchema),
});

export type AnalysisResult = z.infer<typeof analysisResultSchema>;
