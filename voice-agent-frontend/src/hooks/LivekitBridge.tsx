import { useEffect } from "react";

import { useRoomContext } from "@livekit/components-react";
import { RoomEvent, TranscriptionSegment } from "livekit-client";

import { useAppStore } from "../lib/store";

const decoder = new TextDecoder();

export const LivekitBridge = () => {
  const room = useRoomContext();
  const addTranscript = useAppStore((state) => state.addTranscript);
  const addToolEvent = useAppStore((state) => state.addToolEvent);

  useEffect(() => {
    if (!room) return;
    console.info("[ui] LiveKit bridge active", { room: room.name, identity: room.localParticipant.identity });

    const handleTranscription = (segment: TranscriptionSegment) => {
      if (!segment?.text) return;
      console.debug("[ui] transcription", {
        text: segment.text,
        participant: segment.participant?.identity,
        startTime: segment.startTime,
      });
      addTranscript({
        speaker: segment.participant?.identity === room.localParticipant.identity ? "user" : "assistant",
        text: segment.text,
        timestamp: segment.startTime ?? Date.now() / 1000,
        itemId: segment.id ?? crypto.randomUUID(),
      });
    };

    const handleData = (payload: Uint8Array, _participant: any, _kind: any, topic?: string) => {
      if (!topic?.startsWith("app.")) return;
      console.debug("[ui] data message", { topic, size: payload.byteLength });
      try {
        const parsed = JSON.parse(decoder.decode(payload));
        if (parsed.type === "transcript") {
          addTranscript({
            speaker: parsed.speaker ?? "assistant",
            text: parsed.text ?? "",
            timestamp: parsed.timestamp ?? Date.now() / 1000,
            itemId: parsed.item_id ?? crypto.randomUUID(),
          });
        }
        if (parsed.type === "tool") {
          addToolEvent({
            name: parsed.name,
            arguments: parsed.arguments ?? {},
            output: parsed.output,
            timestamp: parsed.timestamp ?? Date.now() / 1000,
            callId: parsed.call_id,
          });
        }
      } catch (err) {
        console.warn("Failed to parse data message", err);
      }
    };

    room.on(RoomEvent.TranscriptionReceived, handleTranscription);
    room.on(RoomEvent.DataReceived, handleData);

    return () => {
      room.off(RoomEvent.TranscriptionReceived, handleTranscription);
      room.off(RoomEvent.DataReceived, handleData);
      console.info("[ui] LiveKit bridge disposed", { room: room.name });
    };
  }, [room, addTranscript, addToolEvent]);

  return null;
};
