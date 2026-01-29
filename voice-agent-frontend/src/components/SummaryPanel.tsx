import type { SummaryRecord } from "../types";

interface SummaryPanelProps {
  summary: SummaryRecord | null;
  loading: boolean;
  onRefresh?: () => void;
}

const normalizeBullets = (text: string) =>
  text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

export function SummaryPanel({ summary, loading, onRefresh }: SummaryPanelProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h3>Latest Summary</h3>
        {onRefresh ? (
          <button className="secondary" type="button" onClick={onRefresh} disabled={loading}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        ) : null}
      </div>
      <div className="panel-body">
        {!summary ? (
          <p className="panel-empty">Summary data will appear once Supabase stores a call record.</p>
        ) : (
          <article className="summary-card">
            <header>
              <small>{new Date(summary.created_at).toLocaleString()}</small>
            </header>
            <ul>
              {normalizeBullets(summary.summary_text).map((line, index) => (
                <li key={`${summary.id}-line-${index}`}>{line}</li>
              ))}
            </ul>
            {summary.preferences ? (
              <details>
                <summary>Preferences JSON</summary>
                <pre className="timeline-json">{JSON.stringify(summary.preferences, null, 2)}</pre>
              </details>
            ) : null}
          </article>
        )}
      </div>
    </section>
  );
}
