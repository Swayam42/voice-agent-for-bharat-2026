'use client';

import { Button } from '@/components/ui/button';

function NotebookMark() {
  return (
    <div className="relative mb-8 flex size-20 items-center justify-center sm:size-24">
      {/* Soft paper ring */}
      <span className="absolute inset-0 rounded-full border border-foreground/12" />
      <span className="absolute inset-2 rounded-full border border-dashed border-foreground/15" />
      {/* Ink blot / friend mark */}
      <svg
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="relative size-10 text-foreground sm:size-12"
        aria-hidden
      >
        <path
          d="M32 10c-8 8-16 14-16 24a16 16 0 1 0 32 0c0-10-8-16-16-24Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="currentColor"
          fillOpacity="0.06"
        />
        <circle cx="26" cy="34" r="1.8" fill="currentColor" />
        <circle cx="38" cy="34" r="1.8" fill="currentColor" />
        <path
          d="M27 41c2.2 2 7.8 2 10 0"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
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

        <p className="font-odia text-sm tracking-wide text-foreground/50">ମୋ ସାଥୀ</p>

        <h1 className="font-display mt-1 text-5xl leading-none tracking-wide text-foreground sm:text-6xl">
          Mo Saathi
        </h1>

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

        <p className="font-hand mt-4 text-sm text-muted-foreground">
          Microphone access is needed to talk
        </p>
      </section>
    </div>
  );
};
