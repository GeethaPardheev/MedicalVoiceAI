import { create } from "zustand";

import type { SummaryRecord, ToolEvent, TranscriptEntry } from "../types";

interface AppState {
  livekitUrl: string | null;
  token: string | null;
  identity: string | null;
  roomName: string | null;
  callerPhone: string | null;
  connecting: boolean;
  transcripts: TranscriptEntry[];
  toolEvents: ToolEvent[];
  summary: SummaryRecord | null;
  setLivekitUrl: (url: string) => void;
  beginConnect: () => void;
  setSession: (params: {
    token: string;
    identity: string;
    roomName: string;
    livekitUrl: string;
    phone: string;
  }) => void;
  clearSession: () => void;
  addTranscript: (entry: TranscriptEntry) => void;
  addToolEvent: (event: ToolEvent) => void;
  setSummary: (record: SummaryRecord | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  livekitUrl: null,
  token: null,
  identity: null,
  roomName: null,
  callerPhone: null,
  connecting: false,
  transcripts: [],
  toolEvents: [],
  summary: null,
  setLivekitUrl: (url) => set({ livekitUrl: url }),
  beginConnect: () => set({ connecting: true }),
  setSession: ({ token, identity, roomName, livekitUrl, phone }) =>
    set({
      token,
      identity,
      roomName,
      livekitUrl,
      callerPhone: phone,
      connecting: false,
      transcripts: [],
      toolEvents: [],
      summary: null,
    }),
  clearSession: () =>
    set({
      token: null,
      identity: null,
      roomName: null,
      callerPhone: null,
      transcripts: [],
      toolEvents: [],
      summary: null,
      connecting: false,
    }),
  addTranscript: (entry) =>
    set((state) => ({ transcripts: [...state.transcripts, entry] })),
  addToolEvent: (event) =>
    set((state) => ({ toolEvents: [...state.toolEvents, event] })),
  setSummary: (record) => set({ summary: record }),
}));
