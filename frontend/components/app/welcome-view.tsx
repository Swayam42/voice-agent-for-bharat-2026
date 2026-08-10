'use client';

import { useEffect, useState } from 'react';
import { BookOpenIcon, UserIcon } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { Button } from '@/components/ui/button';

function NotebookMark() {
  return (
    <div className="relative mb-8 flex size-20 items-center justify-center sm:size-24">
      {/* Soft paper ring */}
      <span className="border-foreground/12 absolute inset-0 rounded-full border" />
      <span className="border-foreground/15 absolute inset-2 rounded-full border border-dashed" />
      {/* Educational Book Mark */}
      <BookOpenIcon className="text-foreground/80 relative size-10 sm:size-12" strokeWidth={1.5} />
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: (isNewSession?: boolean) => void;
  disabled?: boolean;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  disabled = false,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const [showOptions, setShowOptions] = useState(false);
  const [hasExistingSession, setHasExistingSession] = useState(false);

  useEffect(() => {
    // Check if there's an existing ID in localStorage
    const existingId = localStorage.getItem('mo_saathi_user_id');
    if (existingId) {
      setHasExistingSession(true);
    }
  }, []);

  return (
    <div ref={ref} className="flex w-full justify-center px-5">
      <section className="flex w-full max-w-sm flex-col items-center text-center">
        <NotebookMark />

        <h1 className="font-display text-foreground mt-1 text-5xl leading-none tracking-wide sm:text-6xl">
          Mo Saathi
        </h1>
        <p className="font-odia text-1xl text-foreground/50 mt-2 tracking-wide">ମୋ ସାଥୀ</p>

        <p className="font-hand text-muted-foreground mt-4 max-w-[17rem] text-lg leading-snug sm:text-xl">
          Your personal Odia tutor. Master your school subjects with simple, real-world
          explanations.
        </p>

        <Button
          size="lg"
          variant="outline"
          onClick={() => {
            if (hasExistingSession) {
              setShowOptions(true);
            } else {
              onStartCall(false);
            }
          }}
          disabled={disabled}
          className="pencil-box mt-9 h-14 w-full max-w-xs font-hand text-xl tracking-wide text-foreground shadow-none"
        >
          {startButtonText}
        </Button>
      </section>

      {/* Session Prompt Modal */}
      <AnimatePresence>
        {showOptions && (
          <div className="bg-background/80 absolute inset-0 z-50 flex items-center justify-center px-4 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="pencil-box bg-background flex w-full max-w-sm flex-col items-center p-6 text-center sm:p-8"
            >
              <UserIcon className="text-foreground/80 mb-4 size-8" strokeWidth={1.5} />
              <h3 className="font-hand mb-2 text-xl font-bold">Resume Learning?</h3>
              <p className="font-hand text-muted-foreground mb-6">
                You have a saved session. Do you want to continue where you left off, or start fresh?
              </p>
              <div className="flex w-full flex-col gap-3">
                <Button
                  variant="outline"
                  className="pencil-box font-hand bg-background h-12 w-full text-lg shadow-none"
                  onClick={() => onStartCall(false)}
                >
                  Continue Learning
                </Button>
                <Button
                  variant="outline"
                  className="pencil-box font-hand h-12 w-full bg-white text-lg text-black shadow-none hover:bg-gray-100"
                  onClick={() => onStartCall(true)}
                >
                  Start New Session
                </Button>
                <Button
                  variant="ghost"
                  className="font-hand mt-2 h-10 w-full text-base text-muted-foreground shadow-none hover:bg-transparent hover:text-foreground"
                  onClick={() => setShowOptions(false)}
                >
                  Cancel
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
