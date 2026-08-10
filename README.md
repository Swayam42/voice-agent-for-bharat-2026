# Mo Saathi - Odia Voice Tutor

Mo Saathi is a conversational AI agent designed for Odia-speaking students. It helps students practice their school subjects and learn interactively using native Odia language (powered by Sarvam AI for STT and Murf Falcon for TTS).

## Project Structure
- `/backend`: Python LiveKit agent with SQLite memory and function calling tools.
  > **Note on Data (Day 5 Requirement):** The `get_next_exercise` tool uses a **hand-built local dataset** (`backend/src/question_bank.py`) rather than a live external API.
- `/frontend`: Next.js web application for the user interface.

## Quick Start
1. Add `.env.local` to both `/backend` and `/frontend`.
2. Start the backend: `cd backend && uv run python src/agent.py dev`
3. Start the frontend: `cd frontend && pnpm dev`

For more details, see the READMEs in each folder.
