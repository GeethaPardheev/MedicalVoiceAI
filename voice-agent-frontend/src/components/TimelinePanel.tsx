import type { ToolEvent } from "../types";

interface TimelinePanelProps {
  events: ToolEvent[];
}

const formatTime = (timestamp: number) => {
  if (!timestamp) return "";
  return new Date(timestamp * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

export function TimelinePanel({ events }: TimelinePanelProps) {
  return (
    <section className="panel">
      <h3>Tool Timeline</h3>
      <div className="panel-body">
        {events.length === 0 ? (
          <p className="panel-empty">No tool calls yet.</p>
        ) : (
          events.map((event, index) => (
            <article className="timeline-item" key={`${event.callId ?? index}-${event.timestamp}`}>
              <strong>{event.name}</strong>
              <span className="timeline-time">{formatTime(event.timestamp)}</span>
              <pre className="timeline-json">{JSON.stringify(event.arguments, null, 2)}</pre>
              {event.output ? (
                <pre className="timeline-json result">{JSON.stringify(event.output, null, 2)}</pre>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );
}
