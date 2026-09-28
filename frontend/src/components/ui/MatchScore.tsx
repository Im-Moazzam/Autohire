type Band = "strong" | "good" | "partial" | "weak";

const barColor: Record<Band, string> = {
  strong: "bg-score-strong",
  good: "bg-score-good",
  partial: "bg-score-partial",
  weak: "bg-score-weak",
};

const textColor: Record<Band, string> = {
  strong: "text-score-strong",
  good: "text-score-good",
  partial: "text-score-partial",
  weak: "text-score-weak",
};

const bandLabel: Record<Band, string> = {
  strong: "Strong match",
  good: "Good match",
  partial: "Partial match",
  weak: "Weak match",
};

function bandFor(score: number): Band {
  if (score >= 0.8) return "strong";
  if (score >= 0.6) return "good";
  if (score >= 0.4) return "partial";
  return "weak";
}

export interface MatchScoreProps {
  /** 0-1 cosine similarity. Omit while loading. */
  score?: number;
  isLoading?: boolean;
  /** Ranking failed for this candidate (e.g. PARSE_ERROR) — score never landed. */
  errorText?: string;
  /** Defaults to a fixed 160px — pass e.g. "w-full" to fill a wider container. */
  className?: string;
}

export function MatchScore({
  score,
  isLoading = false,
  errorText,
  className = "w-40",
}: MatchScoreProps) {
  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 ${className}`} aria-busy="true">
        <div className="h-2 flex-1 rounded-sm bg-border animate-pulse" />
        <span className="text-helper text-muted">…</span>
      </div>
    );
  }

  if (errorText || score === undefined) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="h-2 flex-1 rounded-sm bg-border" />
        <span className="text-helper text-muted">
          {errorText ?? "Unavailable"}
        </span>
      </div>
    );
  }

  const band = bandFor(score);

  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      role="meter"
      aria-valuenow={Math.round(score * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="h-2 flex-1 rounded-sm bg-border overflow-hidden">
        <div
          className={`h-full ${barColor[band]}`}
          style={{ width: `${Math.round(score * 100)}%` }}
        />
      </div>
      <span className={`text-helper font-semibold ${textColor[band]}`}>
        {Math.round(score * 100)}% · {bandLabel[band]}
      </span>
    </div>
  );
}
