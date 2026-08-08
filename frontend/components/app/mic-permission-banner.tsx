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
      className={cn(
        'mx-auto w-full max-w-md pencil-box bg-background p-5 shadow-sm',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full border border-foreground/15 bg-secondary">
          <MicOffIcon className="size-5 text-foreground" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1 space-y-2 text-left">
          <h2 className="font-display text-xl leading-tight text-foreground">
            Microphone blocked
          </h2>
          <p className="font-hand text-base leading-snug text-muted-foreground">
            Mo Saathi needs your mic to hear you. Please allow microphone access, then try again.
          </p>
          <ol className="font-hand space-y-1 pl-4 text-sm leading-snug text-foreground/70 list-decimal">
            <li>Tap the lock / info icon in your browser address bar</li>
            <li>Set Microphone to Allow</li>
            <li>Reload the page and start learning again</li>
          </ol>
          <div className="flex flex-wrap gap-2 pt-2">
            {onRetry && (
              <Button
                onClick={onRetry}
                className="pencil-box h-11 min-w-[7.5rem] bg-foreground text-black hover:bg-foreground/90 px-5 font-hand text-base"
              >
                Try again
              </Button>
            )}
            {onDismiss && (
              <Button
                variant="outline"
                onClick={onDismiss}
                className="pencil-box h-11 border-2 border-foreground hover:bg-accent px-5 font-hand text-base"
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
