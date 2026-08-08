'use client';

import { Button } from '@/components/ui/button';
import { BookOpenIcon } from 'lucide-react';

function NotebookMark() {
  return (
    <div className="relative mb-8 flex size-20 items-center justify-center sm:size-24">
      {/* Soft paper ring */}
      <span className="absolute inset-0 rounded-full border border-foreground/12" />
      <span className="absolute inset-2 rounded-full border border-dashed border-foreground/15" />
      {/* Educational Book Mark */}
      <BookOpenIcon className="relative size-10 text-foreground/80 sm:size-12" strokeWidth={1.5} />
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  disabled?: boolean;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  disabled = false,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref} className="flex w-full justify-center px-5">
      <section className="flex w-full max-w-sm flex-col items-center text-center">
        <NotebookMark />

        <h1 className="font-display mt-1 text-5xl leading-none tracking-wide text-foreground sm:text-6xl">
          Mo Saathi
        </h1>
        <p className="font-odia mt-2 text-1xl tracking-wide text-foreground/50">ମୋ ସାଥୀ</p>

        <p className="font-hand mt-4 max-w-[17rem] text-lg leading-snug text-muted-foreground sm:text-xl">
          Your personal Odia tutor. Master your school subjects with simple, real-world explanations.
        </p>



        <Button
          size="lg"
          variant="outline"
          onClick={onStartCall}
          disabled={disabled}
          className="pencil-box mt-9 h-14 w-full max-w-xs font-hand text-xl tracking-wide text-foreground shadow-none"
        >
          {startButtonText}
        </Button>
      </section>
    </div>
  );
};
