
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
- **Tools**:
  - `lookup_student_profile`, `save_student_profile`, `forget_me` — Day 3 memory
  - `get_next_exercise` — Day 5 practice questions from local Class 9/10 dataset
  - `schedule_study_reminder`, `cancel_study_reminder`, `list_my_reminders` — Day 6 outbound reminders
  - `create_escalation` — **Day 7** human help requests (see below)
- **Odia Support**: Native Odia TTS and STT processing.

## Day 7 — Human Escalation Setup

Mo Saathi escalates to a human teacher when:
1. The student expresses **emotional distress** (hopelessness, exam anxiety, wanting to give up)
2. The student **repeatedly fails** to understand the same topic after 3+ explanations

### How it works
1. Agent detects one of the two triggers
2. Agent tells the student what info it will share and asks for **consent**
3. If consent granted → saves a concise summary to SQLite → emails the teacher
4. Student receives a **reference ID** (e.g. `ESC-A3B7C2D1`) and an honest timeline

### Email setup (Resend + mail.swayamjethi.me)

1. Create a free account at [resend.com](https://resend.com)
2. Go to **Domains → Add Domain** → enter `mail.swayamjethi.me` (using a subdomain like `mail` is recommended to keep your root MX records clean).
3. Add the 3 DNS records Resend displays to your domain registrar (hostnames like `resend._domainkey.mail` and `send.mail`).
4. Wait for verification (usually < 5 minutes).
5. Copy the API key from Resend dashboard.
6. Fill in `.env`:
   ```
   RESEND_API_KEY=re_your_key_here
   ESCALATION_EMAIL_TO=your-personal@email.com
   ```

> **Note:** The FROM address `mosaathi@mail.swayamjethi.me` only works after the domain is verified in Resend.
> If you skip Resend setup, escalations are still saved to the local DB — only the email notification is skipped.

# Backend — Voice Agent with Murf Falcon TTS

The Python backend for the Voice Agent Starter. It runs a real-time voice AI pipeline using [LiveKit Agents](https://docs.livekit.io/agents), connecting Murf Falcon TTS, Deepgram STT, and Google Gemini into a single conversational agent.

## How It Works

```
User speaks → [Deepgram STT] → text → [Gemini LLM] → response → [Murf Falcon TTS] → audio → User hears
```

LiveKit handles the real-time audio transport. The agent connects to LiveKit as a participant, listens for user speech, and responds with synthesized audio.

## Setup

### 1. Install dependencies

```bash
cd backend
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env.local
```

Fill in your keys in `.env.local`:

| Variable             | Where to get it                                           |
| -------------------- | --------------------------------------------------------- |
| `LIVEKIT_URL`        | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_API_KEY`    | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `LIVEKIT_API_SECRET` | [LiveKit Cloud](https://cloud.livekit.io/) → Settings     |
| `MURF_API_KEY`       | [murf.ai/api/dashboard](https://murf.ai/api/dashboard)    |
| `DEEPGRAM_API_KEY`   | [deepgram.com](https://console.deepgram.com/)             |
| `GOOGLE_API_KEY`     | [aistudio.google.com](https://aistudio.google.com/apikey) |

For LiveKit Cloud users, you can auto-populate LiveKit credentials:

```bash
lk cloud auth
lk app env -w -d .env.local
```

### 3. Download models

```bash
uv run python src/agent.py download-files
```

This downloads Silero VAD and the LiveKit turn detector models.

### 4. Run the agent

```bash
# Development mode (auto-reload)
uv run python src/agent.py dev

# Or test directly in your terminal (no frontend needed)
uv run python src/agent.py console

# Production
uv run python src/agent.py start
```

## Configuration

All configuration lives in [`src/agent.py`](src/agent.py).

### System prompt

The `SYSTEM_PROMPT` constant at the top of `agent.py` controls what your agent does. Change it to build any voice-powered use case.

#### Example prompts

**Customer Support (default):**

```
You are a friendly and efficient customer support agent for a tech company. Help users with account issues, billing questions, and product troubleshooting. Be concise, empathetic, and solution-oriented. If you don't know something, say so honestly and offer to escalate.
```

**Language Tutor:**

```
You are a patient and encouraging language tutor helping the user practice conversational Spanish. Speak primarily in Spanish but switch to English to explain grammar or vocabulary when needed. Correct mistakes gently and suggest better phrasing. Keep conversations natural and fun.
```

**AI Receptionist:**

```
You are a professional receptionist for a medical clinic. Help callers schedule appointments, answer questions about office hours and services, and take messages for doctors. Be warm but efficient. Ask for the caller's name and reason for calling upfront.
```

**Interview Coach:**

```
You are an experienced interview coach. Conduct mock interviews with the user for software engineering roles. Ask one behavioral or technical question at a time, let the user answer fully, then give specific feedback on their response — what was strong, what could improve, and a suggested reframe. Keep the tone encouraging but honest.
```

**Sales Assistant:**

```
You are a knowledgeable sales assistant for an electronics store. Help customers find the right product by asking about their needs, budget, and preferences. Compare options clearly, highlight trade-offs, and make a recommendation. Never be pushy — focus on helping the customer make the best decision for them.
```

**Fitness Coach:**

```
You are an upbeat personal fitness coach. Help users plan workouts, suggest exercises for specific muscle groups, and answer questions about form and technique. Ask about their fitness level and any injuries before recommending exercises. Keep instructions clear and motivating.
```

**Storyteller / Bedtime Narrator:**

```
You are a creative storyteller who tells original bedtime stories for children aged 4–8. Ask the child (or parent) for a character name, a favorite animal, and a setting, then weave a short, calming story. Use vivid but simple language. End each story on a peaceful, sleepy note.
```

**Meeting Summarizer:**

```
You are a meeting assistant. The user will describe what happened in a meeting or read you their notes. Summarize the key decisions, action items (with owners if mentioned), and any open questions. Be concise and structured. Ask clarifying questions if something is ambiguous.
```

**Trivia Game Host:**

```
You are an enthusiastic trivia game host. Ask the user one trivia question at a time from a mix of categories — science, history, pop culture, geography, and sports. Wait for their answer, tell them if they're right or wrong, give a brief fun fact, then move to the next question. Keep score and announce it every 5 questions.
```

**Mental Health Check-in Companion:**

```
You are a gentle, non-clinical wellness companion. Help users talk through their day, reflect on how they're feeling, and practice simple grounding exercises like deep breathing or gratitude lists. You are not a therapist — if the user expresses serious distress or mentions self-harm, gently encourage them to reach out to a professional or crisis helpline.
```

### Voice

Set the `voice` argument in the `murf.TTS(...)` call:

```python
tts=murf.TTS(
    voice="en-US-matthew",    # Change this
    style="Conversation",
    tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
    text_pacing=True
)
```

Some voice options:

| Voice ID | Description                      |
| -------- | -------------------------------- |
| `Anisha` | Indian English, female (default) |
| `Pooja`  | Indian English, female           |
| `Samar`  | Indian English, male             |
| `Amara`  | US English, female               |
| `Hazel`  | UK English, female               |
| `Bertie` | UK English, male                 |
| `Gordon` | US English, male                 |

Browse all 150+ voices: [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library).

### STT (Speech-to-Text)

Default is Deepgram Nova-3. Change in the `AgentSession(stt=...)` call:

```python
stt=deepgram.STT(model="nova-3")
```

### LLM

Default is Google Gemini. To switch:

- **Gemini (default):** Set `GOOGLE_API_KEY` in `.env.local`
- **OpenAI:** Set `OPENAI_API_KEY`, install `livekit-agents[openai]`, and change the `llm=` argument

## Telephony

To connect the agent to a real phone number — answering incoming calls or placing outgoing ones — see [`src/telephony/`](src/telephony/). It contains two self-contained starters (`inbound/` and `outbound/`) that reuse this same voice pipeline, plus SIP trunk and dispatch rule templates.

```bash
uv run python src/telephony/inbound/agent.py dev              # answer calls
uv run python src/telephony/outbound/dial.py --to +15551234567  # place a call
```

No extra dependencies required. Full setup guide: [`src/telephony/README.md`](src/telephony/README.md).

## Testing

The project includes an eval suite based on the LiveKit Agents [testing framework](https://docs.livekit.io/agents/build/testing/):

```bash
uv run pytest
```

Tests are in [`tests/test_agent.py`](tests/test_agent.py) and use LLM-as-judge evaluations to verify the agent behaves correctly (friendly greetings, grounding, refusing harmful requests).

To run tests in CI, you'll need to add `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` as repository secrets.

## Deployment

### Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/tIVCF1?referralCode=cNjn2P&utm_medium=integration&utm_source=template&utm_campaign=generic)

Set these environment variables in Railway:

- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY`
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

### Docker

A production-ready [Dockerfile](Dockerfile) is included:

```bash
docker build -t murf-voice-agent .
docker run --env-file .env.local murf-voice-agent
```

## Project Structure

```
backend/
├── src/
│   ├── agent.py          # Agent entrypoint — pipeline, prompt, config
│   └── telephony/        # Optional — phone call agents
│       ├── README.md     # SIP setup guide
│       ├── inbound/      # agent.py + trunk & dispatch rule templates
│       └── outbound/     # agent.py, dial.py + trunk template
├── tests/
│   └── test_agent.py     # LLM-judged eval suite
├── .env.example           # Environment variable template
├── pyproject.toml         # Python dependencies (uv)
├── Dockerfile             # Production container
└── railway.toml           # Railway deploy config
```

## Links

- [Murf Falcon TTS Docs](https://murf.ai/api/docs/text-to-speech/streaming)
- [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)
- [LiveKit Agents Docs](https://docs.livekit.io/agents)
- [Deepgram Nova-3 Docs](https://developers.deepgram.com)

---

## Day 8 — Call Analytics

### What counts as a successful call?

Mo Saathi belongs to the **Learning & Literacy** track.

A call is **successful** when the student reaches and attempts at least one
practice exercise — i.e. the `get_next_exercise` tool is called during the
session.

A call is **failed** when the session ends before any exercise is reached
(student disconnected too early, changed topic, or the session was abandoned).

**Success is determined deterministically** — no LLM call is made at call end.
The signal is a simple flag set by the tool in real-time.

### Data model

Analytics are stored in the shared SQLite database (`backend/data/mo_saathi.db`)
in the `call_sessions` table:

| Column              | Type    | Description                                |
|---------------------|---------|--------------------------------------------|
| `session_id`        | TEXT PK | LiveKit room name (stable call identity)   |
| `user_id`           | TEXT    | Participant identity from LiveKit          |
| `call_type`         | TEXT    | `inbound` (browser) or `outbound` (SIP)    |
| `language`          | TEXT    | STT language code (`od-IN`)                |
| `outcome`           | TEXT    | `in_progress` → `successful` or `failed`   |
| `exercise_attempted`| INTEGER | 1 if get_next_exercise was called          |
| `tool_calls_count`  | INTEGER | Total number of tool invocations           |
| `success_reason`    | TEXT    | `exercise_tool_called` (when successful)   |
| `failure_reason`    | TEXT    | `ended_before_exercise` (when failed)      |
| `started_at`        | TEXT    | ISO-8601 UTC timestamp                     |
| `ended_at`          | TEXT    | ISO-8601 UTC timestamp (NULL while live)   |
| `duration_sec`      | INTEGER | Wall-clock seconds (NULL while live)       |

The table is created automatically at agent startup and migrates safely on
existing databases using `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.

### How dashboard numbers are calculated

All metrics come from simple SQL aggregates — no LLM, no transcript processing:

```sql
-- Total / Successful / Failed
SELECT COUNT(*),
       SUM(CASE WHEN outcome='successful' THEN 1 ELSE 0 END),
       SUM(CASE WHEN outcome='failed'     THEN 1 ELSE 0 END)
FROM call_sessions;

-- Success rate
ROUND(successful / total * 100, 1)

-- Average duration
AVG(duration_sec)
```

### Privacy

The analytics dashboard does **not** display:
- Full user IDs (anonymised to an 8-character hash)
- Phone numbers or email addresses
- Conversation transcripts
- Escalation content
- Raw student messages

Session identifiers shown in the UI are the last 6 characters of the LiveKit
room name (e.g. `4505`) — non-PII slugs assigned by LiveKit.

### Viewing the dashboard locally

1. Start the backend: `uv run python src/agent.py dev`
2. Start the frontend: `cd frontend && pnpm dev`
3. Open: **http://localhost:3000/analytics**

The dashboard auto-refreshes every 10 seconds. Make a learning call and ask
the agent for a practice question — the Successful count will increment.

## License

MIT — see [LICENSE](LICENSE).

