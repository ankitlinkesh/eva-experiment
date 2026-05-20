# Eva Agent

Eva is a clean rebuild of the desktop assistant as a modular Python/FastAPI agent with a responsive phone-ready UI.

## Run

```powershell
cd "C:\Users\HP\Documents\Codex\eva-agent"
.\.venv\Scripts\python.exe -m uvicorn backend.eva.main:app --host 0.0.0.0 --port 8765
```

Open on the laptop:

```text
http://127.0.0.1:8765
```

Open on a phone connected to the same Wi-Fi:

```text
http://<laptop-ip>:8765
```

## Current MVP

- Futuristic local web UI for laptop and phone.
- Instant desktop-command layer for app launching, folders, web search, URLs, media keys, lock, and guarded power actions.
- Hybrid model routing: deterministic desktop commands first, Gemini `gemini-2.5-flash` for smart cloud replies, and local Ollama fallback with `qwen2.5:1.5b` / `mistral:7b`.
- On-demand screen snapshot only when requested; no always-on camera/screen watching.
- SQLite conversation memory.
- Modular seams for future voice-to-voice.

## Example Commands

```text
open chrome
open codex
open downloads
search for best local AI agents
visit youtube.com
volume up
mute
lock laptop
shutdown
confirm shutdown
```

`shutdown`, `restart`, `sleep`, and `sign out` require the word `confirm`.

## Architecture

Read `docs/ARCHITECTURE.md`.



