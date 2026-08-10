# Mo Saathi - Frontend

The frontend is a React application built with Next.js, styled with Tailwind CSS, and powered by LiveKit components.

## Setup & Running

1. Make sure you have `pnpm` installed.
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. Copy `.env.example` to `.env.local` and add your LiveKit credentials (this must match the backend).
4. Run the development server:
   ```bash
   pnpm dev
   ```

## Features
- Connects directly to the Python backend LiveKit room.
- Provides a user-friendly modal to select "Continue Learning" or "Start New Session".
- Supports conversational transcripts, visualizers, and exporting chat history.
