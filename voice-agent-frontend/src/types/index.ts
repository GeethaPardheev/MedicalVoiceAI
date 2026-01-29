export type TranscriptEntry = {
  speaker: "user" | "assistant" | "system";
  text: string;
  timestamp: number;
  itemId: string;
};

export type ToolEvent = {
  name: string;
  arguments: Record<string, unknown>;
  output?: unknown;
  timestamp: number;
  callId?: string | null;
};

export type SummaryRecord = {
  id: string;
  summary_text: string;
  preferences?: Record<string, unknown>;
  appointments_in_call?: unknown;
  cost_breakdown?: Record<string, unknown>;
  action_items?: string[];
  timeline?: ToolEvent[];
  transcript?: TranscriptEntry[];
  created_at: string;
};
