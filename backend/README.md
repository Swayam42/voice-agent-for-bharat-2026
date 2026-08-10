# Mo Saathi - Backend

The backend is built with Python and the LiveKit Agents SDK. It handles the AI logic, STT (Sarvam), TTS (Murf Falcon), LLM (Google Gemini), and SQLite database for memory.

## Setup & Running

1. Ensure you have Python 3.10+ installed and the `uv` package manager.
2. Copy `.env.example` to `.env.local` and add your API keys.
3. Download required models:
   ```bash
   uv run python src/agent.py download-files
   ```
4. Run the agent server:
   ```bash
   uv run python src/agent.py dev
   ```

## Features
- **Persistent Memory**: Uses SQLite to store student profiles across sessions.
- **Tools**: Includes `lookup_student_profile`, `save_student_profile`, and `get_next_exercise`.
  > **Note on Data (Day 5 Requirement):** The `get_next_exercise` tool uses a **hand-built local dataset** (`backend/src/question_bank.py`) rather than a live external API.
- **Odia Support**: Native Odia TTS and STT processing.
