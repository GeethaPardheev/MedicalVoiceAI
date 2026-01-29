import { useEffect, useState } from "react";

import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";

import { LiveCallStage } from "./components/LiveCallStage";
import { SessionForm } from "./components/SessionForm";
import { SummaryPanel } from "./components/SummaryPanel";
import { TimelinePanel } from "./components/TimelinePanel";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { LivekitBridge } from "./hooks/LivekitBridge";
import { fetchConfig, fetchSummaries, requestSession } from "./lib/api";
import { useAppStore } from "./lib/store";

export default function App() {
  const [displayName, setDisplayName] = useState("Aida QA");
  const [phoneNumber, setPhoneNumber] = useState("+15555550123");
  const [roomName, setRoomName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const livekitUrl = useAppStore((state) => state.livekitUrl);
  const token = useAppStore((state) => state.token);
  const identity = useAppStore((state) => state.identity);
  const activeRoom = useAppStore((state) => state.roomName);
  const callerPhone = useAppStore((state) => state.callerPhone);
  const connecting = useAppStore((state) => state.connecting);
  const transcripts = useAppStore((state) => state.transcripts);
  const toolEvents = useAppStore((state) => state.toolEvents);
  const summary = useAppStore((state) => state.summary);

  const setLivekitUrl = useAppStore((state) => state.setLivekitUrl);
  const beginConnect = useAppStore((state) => state.beginConnect);
  const setSession = useAppStore((state) => state.setSession);
  const clearSession = useAppStore((state) => state.clearSession);
  const setSummary = useAppStore((state) => state.setSummary);

  useEffect(() => {
    fetchConfig()
      .then((config) => {
        if (config?.livekit_url) {
          setLivekitUrl(config.livekit_url);
          console.info("[ui] loaded backend config", config);
        }
      })
      .catch((err) => console.warn("[ui] failed to load backend config", err));
  }, [setLivekitUrl]);

  const connected = Boolean(token && livekitUrl);

  const loadLatestSummary = async (phone: string) => {
    if (!phone) return;
    setSummaryLoading(true);
    console.info("[ui] fetching latest summary", { phone });
    try {
      const records = await fetchSummaries(phone, 1);
      setSummary(records?.[0] ?? null);
      console.info("[ui] summary response", { hasRecord: Boolean(records?.length) });
    } catch (err) {
      console.warn("[ui] unable to fetch summaries", err);
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleConnect = async () => {
    if (!displayName.trim() || !phoneNumber.trim()) {
      setError("Display name and phone are required");
      return;
    }
    setError(null);
    beginConnect();
    console.info("[ui] starting connect flow", { displayName, phoneNumber, roomName: roomName || undefined });
    try {
      const payload: { display_name: string; phone_number: string; room_name?: string } = {
        display_name: displayName.trim(),
        phone_number: phoneNumber.trim(),
      };
      if (roomName.trim()) {
        payload.room_name = roomName.trim();
      }
      const session = await requestSession(payload);
      setSession({
        token: session.token,
        identity: session.identity,
        roomName: session.room_name,
        livekitUrl: session.livekit_url,
        phone: phoneNumber.trim(),
      });
      console.info("[ui] session established", { room: session.room_name, identity: session.identity });
      await loadLatestSummary(phoneNumber.trim());
    } catch (err) {
      console.error("[ui] session request failed", err);
      const message = err instanceof Error ? err.message : "Failed to start session";
      setError(message);
      clearSession();
    }
  };

  const handleDisconnect = () => {
    console.info("[ui] disconnect requested");
    clearSession();
  };

  const handleRefreshSummary = () => {
    if (callerPhone) {
      console.info("[ui] manual summary refresh", { phone: callerPhone });
      void loadLatestSummary(callerPhone);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1 className="hero-title">Medical voice agent cockpit</h1>
        <p className="hero-subtitle">
          Issue a LiveKit session token, monitor transcripts, observe tool calls, and review Supabase
          summaries for every call handled by the realtime worker.
        </p>
        <SessionForm
          displayName={displayName}
          phoneNumber={phoneNumber}
          roomName={roomName}
          connecting={connecting}
          connected={connected}
          error={error}
          onDisplayNameChange={setDisplayName}
          onPhoneChange={setPhoneNumber}
          onRoomNameChange={setRoomName}
          onSubmit={handleConnect}
        />
      </aside>

      <main>
        <LiveCallStage
          connecting={connecting}
          connected={connected}
          roomName={activeRoom}
          identity={identity}
          callerPhone={callerPhone}
          onDisconnect={handleDisconnect}
        />

        <div className="panel-grid">
          <TimelinePanel events={toolEvents} />
          <TranscriptPanel entries={transcripts} />
          <SummaryPanel summary={summary} loading={summaryLoading} onRefresh={handleRefreshSummary} />
        </div>
      </main>

      {connected && token && livekitUrl ? (
        <LiveKitRoom serverUrl={livekitUrl} token={token} audio video={false} connect>
          <LivekitBridge />
          <RoomAudioRenderer />
        </LiveKitRoom>
      ) : null}
    </div>
  );
}
