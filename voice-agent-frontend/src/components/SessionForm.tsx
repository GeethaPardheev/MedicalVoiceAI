import type { FormEvent } from "react";

interface SessionFormProps {
  displayName: string;
  phoneNumber: string;
  roomName: string;
  connecting: boolean;
  connected: boolean;
  error: string | null;
  onDisplayNameChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onRoomNameChange: (value: string) => void;
  onSubmit: () => Promise<void> | void;
}

export function SessionForm({
  displayName,
  phoneNumber,
  roomName,
  connecting,
  connected,
  error,
  onDisplayNameChange,
  onPhoneChange,
  onRoomNameChange,
  onSubmit,
}: SessionFormProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="field-group">
        <label htmlFor="displayName">Caller display name</label>
        <input
          id="displayName"
          name="displayName"
          autoComplete="name"
          value={displayName}
          onChange={(event) => onDisplayNameChange(event.target.value)}
          placeholder="Dr. Rivera"
          disabled={connecting || connected}
          required
        />
      </div>

      <div className="field-group">
        <label htmlFor="phoneNumber">Caller phone number</label>
        <input
          id="phoneNumber"
          name="phoneNumber"
          autoComplete="tel"
          value={phoneNumber}
          onChange={(event) => onPhoneChange(event.target.value)}
          placeholder="+15555550123"
          disabled={connecting || connected}
          required
        />
      </div>

      <div className="field-group">
        <label htmlFor="roomName">LiveKit room (optional)</label>
        <input
          id="roomName"
          name="roomName"
          value={roomName}
          onChange={(event) => onRoomNameChange(event.target.value)}
          placeholder="Leave blank for auto"
          disabled={connecting || connected}
        />
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <button className="primary" type="submit" disabled={connecting || connected}>
        {connecting ? "Connecting..." : connected ? "Connected" : "Connect & Join"}
      </button>
    </form>
  );
}
