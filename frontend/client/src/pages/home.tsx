import { useState, useCallback, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import type { AnalysisResult, Insight } from "@shared/schema";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { PerplexityAttribution } from "@/components/PerplexityAttribution";
import {
  Upload,
  Loader2,
  Target,
  RotateCcw,
  MessageSquare,
  CheckCircle2,
  Sparkles,
  Scan,
  ArrowUpRight,
  CircleDot,
} from "lucide-react";

const API_BASE = "__PORT_5000__".startsWith("__") ? "" : "__PORT_5000__";

/* ────────────────────────────────────────────────────────────────────────────
   Status styling
   ────────────────────────────────────────────────────────────────────────── */

type MetricStatus = "good" | "watch" | "fix";

const STATUS_STYLES: Record<
  MetricStatus,
  { dot: string; bg: string; border: string; text: string; badge: string }
> = {
  good: {
    dot: "bg-emerald-400",
    bg: "bg-emerald-500/5",
    border: "border-emerald-500/15",
    text: "text-emerald-400",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  watch: {
    dot: "bg-amber-400",
    bg: "bg-amber-500/5",
    border: "border-amber-500/15",
    text: "text-amber-400",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  fix: {
    dot: "bg-red-400",
    bg: "bg-red-500/5",
    border: "border-red-500/15",
    text: "text-red-400",
    badge: "bg-red-500/10 text-red-400 border-red-500/20",
  },
};

const CATEGORY_LABELS: Record<string, { label: string; icon: typeof Scan }> = {
  setup: { label: "Setup", icon: Target },
  backswing: { label: "Backswing", icon: ArrowUpRight },
  impact: { label: "Impact", icon: CircleDot },
};

/* ────────────────────────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────────────────────── */

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const analyzeMutation = useMutation({
    mutationFn: async (formData: FormData): Promise<AnalysisResult> => {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Analysis failed");
      }
      return data;
    },
    onSuccess: (data) => {
      setResult(data);
    },
    onError: (err: Error) => {
      toast({
        title: "Analysis failed",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) setFile(f);
    },
    []
  );

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f && (f.type.startsWith("video/") || f.name.match(/\.(mp4|mov)$/i))) {
      setFile(f);
    }
  }, []);

  const handleSubmit = useCallback(() => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    // No handedness — auto-detected by backend
    setResult(null);
    analyzeMutation.mutate(fd);
  }, [file, analyzeMutation]);

  const handleReset = useCallback(() => {
    setFile(null);
    setResult(null);
    analyzeMutation.reset();
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [analyzeMutation]);

  const isLoading = analyzeMutation.isPending;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border/50 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          <SwingLogo />
          <span className="text-sm font-semibold tracking-tight">SwingAI</span>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 ml-1 border-primary/30 text-primary">
            v2
          </Badge>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 px-4 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Hero text */}
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight">
              Analyze Your Swing
            </h1>
            <p className="text-sm text-muted-foreground">
              Upload a face-on swing video. We auto-detect your handedness
              and analyze setup, backswing, and impact.
            </p>
          </div>

          {!result ? (
            /* Upload + Controls */
            <div className="space-y-5">
              {/* Drop zone */}
              <div
                data-testid="drop-zone"
                className={`
                  relative rounded-lg border-2 border-dashed transition-colors cursor-pointer
                  ${
                    dragActive
                      ? "border-primary bg-primary/5"
                      : file
                      ? "border-primary/40 bg-card"
                      : "border-border hover:border-muted-foreground/30"
                  }
                `}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/quicktime,.mp4,.mov"
                  className="hidden"
                  onChange={handleFileChange}
                  data-testid="input-file"
                />
                <div className="flex flex-col items-center justify-center py-12 px-4 text-center gap-3">
                  {file ? (
                    <>
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <CheckCircle2 className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{file.name}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {(file.size / (1024 * 1024)).toFixed(1)} MB
                          <span className="mx-1.5">&middot;</span>
                          Click to change
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                        <Upload className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          Drop your swing video here
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          MP4 or MOV, up to 10 MB
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Submit */}
              <Button
                data-testid="button-analyze"
                size="lg"
                className="w-full"
                disabled={!file || isLoading}
                onClick={handleSubmit}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing swing...
                  </>
                ) : (
                  <>
                    <Target className="w-4 h-4 mr-2" />
                    Analyze Swing
                  </>
                )}
              </Button>

              {isLoading && (
                <p className="text-xs text-muted-foreground text-center">
                  Extracting frames, detecting handedness, and running pose
                  analysis — about 15-20 seconds.
                </p>
              )}
            </div>
          ) : (
            /* ──── Results View ──── */
            <div className="space-y-6">
              {/* Action bar */}
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="secondary" className="text-xs" data-testid="badge-handedness">
                  {result.handedness === "right"
                    ? "Right-handed"
                    : "Left-handed"}
                </Badge>
                {result.handedness_source === "auto" && (
                  <Badge
                    variant="outline"
                    className="text-[10px] px-1.5 py-0 h-4 border-primary/30 text-primary gap-1"
                    data-testid="badge-autodetect"
                  >
                    <Scan className="w-3 h-3" />
                    Auto-detected
                  </Badge>
                )}
                <div className="flex-1" />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  data-testid="button-reset"
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                  New analysis
                </Button>
              </div>

              {/* AI Coaching Summary — concise hero card */}
              {result.coaching_summary && (
                <Card
                  className="border-primary/20 bg-primary/5"
                  data-testid="coaching-summary"
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                        <MessageSquare className="w-4 h-4 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <h2 className="text-sm font-semibold">
                            Coach's Take
                          </h2>
                          <Sparkles className="w-3.5 h-3.5 text-primary/60" />
                        </div>
                        <p
                          className="text-sm leading-relaxed text-muted-foreground"
                          data-testid="coaching-text"
                        >
                          {result.coaching_summary}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Insight cards grouped by swing phase */}
              {result.insights && result.insights.length > 0 && (
                <div className="space-y-5">
                  {(["setup", "backswing", "impact"] as const).map((cat) => {
                    const catInsights = result.insights.filter(
                      (i: Insight) => i.category === cat
                    );
                    if (catInsights.length === 0) return null;
                    const catConfig = CATEGORY_LABELS[cat];
                    const CatIcon = catConfig.icon;

                    return (
                      <div key={cat}>
                        <h2 className="text-sm font-semibold mb-2.5 flex items-center gap-1.5">
                          <CatIcon className="w-4 h-4 text-primary" />
                          {catConfig.label}
                        </h2>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                          {catInsights.map((insight: Insight) => {
                            const styles =
                              STATUS_STYLES[
                                insight.status as MetricStatus
                              ];
                            return (
                              <Card
                                key={insight.key}
                                className={`${styles.bg} ${styles.border} border`}
                                data-testid={`insight-${insight.key}`}
                              >
                                <CardContent className="p-3">
                                  <div className="flex items-center justify-between gap-2 mb-1">
                                    <p className="text-xs font-medium text-foreground">
                                      {insight.label}
                                    </p>
                                    <p className="text-sm font-semibold font-mono tracking-tight">
                                      {insight.key ===
                                        "hip_shift_toward_target_units" ||
                                      insight.key ===
                                        "shoulder_tilt_deg_impact"
                                        ? Math.abs(insight.value).toFixed(1)
                                        : Number.isInteger(insight.value)
                                        ? insight.value
                                        : insight.value.toFixed(1)}
                                      <span className="text-[10px] text-muted-foreground ml-0.5">
                                        {insight.unit}
                                      </span>
                                    </p>
                                  </div>
                                  <div className="flex items-center gap-1.5">
                                    <span
                                      className={`w-1.5 h-1.5 rounded-full ${styles.dot} shrink-0`}
                                    />
                                    <span
                                      className={`text-[11px] font-medium ${styles.text}`}
                                    >
                                      {insight.description}
                                    </span>
                                  </div>
                                </CardContent>
                              </Card>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Tips — actionable advice */}
              {result.tips.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold mb-2.5 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-primary" />
                    Practice Tips
                  </h2>
                  <div className="space-y-2">
                    {result.tips.map((t, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2.5 text-sm text-muted-foreground"
                        data-testid={`tip-${i}`}
                      >
                        <span className="text-primary mt-1 text-xs font-bold shrink-0">
                          {i + 1}.
                        </span>
                        <span>{t}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Face-on swing analysis powered by MediaPipe Pose
          </p>
          <PerplexityAttribution />
        </div>
      </footer>
    </div>
  );
}

function SwingLogo() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="SwingAI Logo"
    >
      <circle cx="12" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M12 8.5V15M12 15L9 20M12 15L15 20"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M7 11.5L12 10L17 8"
        stroke="hsl(145, 55%, 42%)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="17" cy="8" r="1" fill="hsl(145, 55%, 42%)" />
    </svg>
  );
}
