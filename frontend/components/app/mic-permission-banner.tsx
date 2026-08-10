'use client';

import { MicOffIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

interface MicPermissionBannerProps {
  open: boolean;
  onDismiss?: () => void;
  onRetry?: () => void;
  className?: string;
}

export function MicPermissionBanner({
  open,
  onDismiss,
  onRetry,
  className,
}: MicPermissionBannerProps) {
  if (!open) return null;

  return (
    <div
      role="alert"
      className={cn('pencil-box bg-background mx-auto w-full max-w-md p-5 shadow-sm', className)}
    >
      <div className="flex items-start gap-3">
        <div className="border-foreground/15 bg-secondary mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full border">
          <MicOffIcon className="text-foreground size-5" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1 space-y-2 text-left">
          <h2 className="font-display text-foreground text-xl leading-tight">Microphone blocked</h2>
          <p className="font-hand text-muted-foreground text-base leading-snug">
            Mo Saathi needs your mic to hear you. Please allow microphone access, then try again.
          </p>
          <ol className="font-hand text-foreground/70 list-decimal space-y-1 pl-4 text-sm leading-snug">
            <li>Tap the lock / info icon in your browser address bar</li>
            <li>Set Microphone to Allow</li>
            <li>Reload the page and start learning again</li>
          </ol>
          <div className="flex flex-wrap gap-2 pt-2">
            {onRetry && (
              <Button
                onClick={onRetry}
                className="pencil-box bg-foreground hover:bg-foreground/90 font-hand h-11 min-w-[7.5rem] px-5 text-base text-black"
              >
                Try again
              </Button>
            )}
            {onDismiss && (
              <Button
                variant="outline"
                onClick={onDismiss}
                className="pencil-box border-foreground hover:bg-accent font-hand h-11 border-2 px-5 text-base"
              >
                Dismiss
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
