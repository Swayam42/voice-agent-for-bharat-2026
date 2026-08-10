'use client';

import { type AgentState } from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';

export type UiPhase = 'ready' | 'connecting' | 'listening' | 'speaking' | 'thinking' | 'ended';

export function mapAgentStateToPhase(state?: AgentState): Exclude<UiPhase, 'ready' | 'ended'> {
  switch (state) {
    case 'speaking':
      return 'speaking';
    case 'thinking':
      return 'thinking';
    case 'listening':
    case 'idle':
    case 'pre-connect-buffering':
      return 'listening';
    case 'connecting':
    case 'initializing':
    default:
      return 'connecting';
  }
}

const STATUS_COPY: Record<
  Exclude<UiPhase, 'ready'>,
  { title: string; subtitle: string; odia?: string }
> = {
  connecting: {
    title: 'Connecting',
    subtitle: 'Saathi is joining — please wait',
    odia: 'ଦୟାକରି ଅପେକ୍ଷା କରନ୍ତୁ',
  },
  listening: {
    title: 'Listening to you',
    subtitle: 'Speak naturally — Saathi is ready',
    odia: 'ତୁମେ କହ, ମୁଁ ଶୁଣୁଛି',
  },
  speaking: {
    title: 'Saathi is speaking',
    subtitle: 'Listen carefully — then ask more',
    odia: 'ସାଥୀ କହୁଛି',
  },
  thinking: {
    title: 'Thinking',
    subtitle: 'Finding a simple way to explain',
    odia: 'ଭାବୁଛି…',
  },
  ended: {
    title: 'Call ended',
    subtitle: 'Ready when you are',
    odia: 'ପୁଣି ଆରମ୍ଭ କରିପାରିବ',
  },
};

interface AgentStatusProps {
  phase: Exclude<UiPhase, 'ready'>;
  className?: string;
  compact?: boolean;
}

export function AgentStatus({ phase, className, compact = false }: AgentStatusProps) {
  const copy = STATUS_COPY[phase];

  return (
    <div
      className={cn(
        'flex flex-col items-center text-center',
        compact ? 'gap-1' : 'gap-2',
        className
      )}
      aria-live="polite"
    >
      <div
        className={cn(
          'pencil-box bg-background pointer-events-none inline-flex items-center gap-2 px-4 py-1.5',
          phase === 'connecting' && 'border-foreground/25'
        )}
      >
        <StatusDot phase={phase} />
        <span className="font-display text-foreground text-lg leading-none tracking-wide sm:text-xl">
          {copy.title}
        </span>
      </div>

      {!compact && (
        <>
          <p className="font-hand text-muted-foreground max-w-[18rem] text-base leading-snug sm:text-lg">
            {copy.subtitle}
          </p>
          {copy.odia && (
            <p className="font-odia text-foreground/55 text-sm sm:text-base">{copy.odia}</p>
          )}
        </>
      )}
    </div>
  );
}

function StatusDot({ phase }: { phase: Exclude<UiPhase, 'ready'> }) {
  const isActive = phase === 'listening' || phase === 'speaking' || phase === 'thinking';

  return (
    <span className="relative flex size-2.5 items-center justify-center" aria-hidden>
      {isActive && (
        <span
          className={cn(
            'bg-foreground/40 absolute inset-0 rounded-full',
            phase === 'speaking' ? 'animate-ping' : 'ink-breathe'
          )}
        />
      )}
      <span
        className={cn(
          'bg-foreground relative size-2 rounded-full',
          phase === 'connecting' && 'ink-breathe',
          phase === 'ended' && 'opacity-40'
        )}
      />
    </span>
  );
}
