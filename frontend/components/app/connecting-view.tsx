'use client';

import { AgentStatus } from '@/components/app/agent-status';

export function ConnectingView({ ref }: React.ComponentProps<'div'>) {
  return (
    <div ref={ref} className="flex w-full justify-center px-5">
      <section className="flex w-full max-w-sm flex-col items-center text-center">
        <div className="relative mb-10 flex size-28 items-center justify-center sm:size-32">
          <span className="ink-breathe pencil-circle pointer-events-none absolute inset-0 opacity-40" />
          <span className="pencil-circle pointer-events-none absolute inset-4 opacity-20" />
          <span className="pencil-circle pointer-events-none relative flex size-14 items-center justify-center bg-background shadow-none opacity-60">
            <span className="flex gap-1.5">
              <span className="ink-dot size-1.5 rounded-full bg-foreground" />
              <span className="ink-dot size-1.5 rounded-full bg-foreground" />
              <span className="ink-dot size-1.5 rounded-full bg-foreground" />
            </span>
          </span>
        </div>

        <AgentStatus phase="connecting" />
      </section>
    </div>
  );
}
