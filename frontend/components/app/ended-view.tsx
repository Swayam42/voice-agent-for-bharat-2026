'use client';

import { Button } from '@/components/ui/button';

interface EndedViewProps {
  onRestart: () => void;
}

export function EndedView({ onRestart, ref }: React.ComponentProps<'div'> & EndedViewProps) {
  return (
    <div ref={ref} className="flex w-full justify-center px-5">
      <section className="flex w-full max-w-sm flex-col items-center text-center">
        <p className="font-odia mt-6 text-sm text-foreground/50">କଲ୍ ଶେଷ</p>
        <h1 className="font-display mt-1 text-4xl leading-none tracking-wide text-foreground sm:text-5xl">
          Call ended
        </h1>
        <p className="font-hand mt-3 max-w-[16rem] text-lg leading-snug text-muted-foreground">
          Nice work. Come back anytime you want to learn something new.
        </p>

        <div className="mt-8 flex w-full max-w-xs flex-col gap-3">
          <Button
            size="lg"
            variant="outline"
            onClick={onRestart}
            className="pencil-box h-14 w-full font-hand text-xl tracking-wide shadow-none"
          >
            Start again
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={() => window.location.reload()}
            className="pencil-box h-14 w-full border-foreground/30 font-hand text-xl tracking-wide shadow-none hover:bg-accent"
          >
            Home
          </Button>
        </div>
      </section>
    </div>
  );
}
