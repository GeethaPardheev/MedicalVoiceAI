interface LiveCallStageProps {
  connecting: boolean;
  connected: boolean;
  roomName: string | null;
  identity: string | null;
  callerPhone: string | null;
  onDisconnect: () => void;
}

const statusCopy = (connecting: boolean, connected: boolean) => {
  if (connecting) {
    return "Requesting LiveKit token";
  }
  if (connected) {
    return "Agent is live in the room";
  }
  return "Fill the form to start a call";
};

export function LiveCallStage({
  connecting,
  connected,
  roomName,
  identity,
  callerPhone,
  onDisconnect,
}: LiveCallStageProps) {
  return (
    <section className="panel stage-panel">
      <div className="status-pill">{statusCopy(connecting, connected)}</div>
      <h2>Realtime Agent Stage</h2>
      <p className="stage-caption">
        The LiveKit worker renders the voiced agent in this virtual stage. Keep the tab active so
        audio output keeps streaming while the backend drives speech + tool invocations.
      </p>

      <dl className="stage-meta">
        <div>
          <dt>Room</dt>
          <dd>{roomName ?? "Pending"}</dd>
        </div>
        <div>
          <dt>Identity</dt>
          <dd>{identity ?? "-"}</dd>
        </div>
        <div>
          <dt>Caller</dt>
          <dd>{callerPhone ?? "+1 ???"}</dd>
        </div>
      </dl>

      {connected ? (
        <button className="secondary" onClick={onDisconnect} type="button">
          End Session
        </button>
      ) : null}
    </section>
  );
}
