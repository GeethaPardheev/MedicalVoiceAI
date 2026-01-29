import type { TranscriptEntry } from "../types";

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
}

const formatTimestamp = (timestamp: number) => {
  if (!timestamp) return "";
  return new Date(timestamp * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};

export function TranscriptPanel({ entries }: TranscriptPanelProps) {
  return (
    <section className="panel">
      <h3>Transcript</h3>
      <div className="panel-body">
        {entries.length === 0 ? (
          <p className="panel-empty">No transcript collected.</p>
        ) : (
          entries.map((entry) => (
            <article className="transcript-entry" data-speaker={entry.speaker} key={entry.itemId}>
              <header>
                <strong>{entry.speaker.toUpperCase()}</strong>
                <span>{formatTimestamp(entry.timestamp)}</span>
              </header>
              <p>{entry.text}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
