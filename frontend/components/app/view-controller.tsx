'use client';

import { useCallback, useEffect, useState } from 'react';
import { ConnectionState, MediaDeviceFailure } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import { useTheme } from 'next-themes';
import type { AppConfig } from '@/app-config';
import { ConnectingView } from '@/components/app/connecting-view';
import { EndedView } from '@/components/app/ended-view';
import { MicPermissionBanner } from '@/components/app/mic-permission-banner';
import { SessionView } from '@/components/app/session-view';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionConnectingView = motion.create(ConnectingView);
const MotionSessionView = motion.create(SessionView);
const MotionEndedView = motion.create(EndedView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1, y: 0 },
    hidden: { opacity: 0, y: 8 },
  },
  initial: 'hidden' as const,
  animate: 'visible' as const,
  exit: 'hidden' as const,
  transition: {
    duration: 0.35,
    ease: 'easeOut' as const,
  },
};

type Screen = 'ready' | 'connecting' | 'session' | 'ended';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const session = useSessionContext();
  const { isConnected, start, connectionState, room } = session;
  const { resolvedTheme } = useTheme();

  const [screen, setScreen] = useState<Screen>('ready');
  const [micDenied, setMicDenied] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  // Sync LiveKit connection into our simple screen machine
  useEffect(() => {
    if (connectionState === ConnectionState.Connecting) {
      setScreen('connecting');
      return;
    }
    if (isConnected) {
      setScreen('session');
      return;
    }
    // Disconnected: if we were in a live session, show the ended screen
    setScreen((prev) => (prev === 'session' ? 'ended' : prev));
  }, [connectionState, isConnected]);

  // Media device / mic permission errors from the room
  useEffect(() => {
    const onMediaDevicesError = (error: Error) => {
      const failure = MediaDeviceFailure.getFailure(error);
      if (
        failure === MediaDeviceFailure.PermissionDenied ||
        failure === MediaDeviceFailure.DeviceInUse ||
        /permission|NotAllowed|Denied/i.test(error.message)
      ) {
        setMicDenied(true);
      }
    };

    room.on('mediaDevicesError', onMediaDevicesError);
    return () => {
      room.off('mediaDevicesError', onMediaDevicesError);
    };
  }, [room]);

  const handleStart = useCallback(async () => {
    setStartError(null);
    setMicDenied(false);
    setScreen('connecting');

    try {
      // Probe mic permission early so we can show a clear message
      if (typeof navigator !== 'undefined' && navigator.mediaDevices?.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          stream.getTracks().forEach((t) => t.stop());
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          if (/Permission|NotAllowed|Denied/i.test(message) || (err as { name?: string })?.name === 'NotAllowedError') {
            setMicDenied(true);
            setScreen('ready');
            return;
          }
        }
      }

      await start({
        tracks: {
          microphone: { enabled: true },
          camera: { enabled: false },
          screenShare: { enabled: false },
        },
      });
    } catch (err) {
      console.error('Failed to start session', err);
      const message = err instanceof Error ? err.message : 'Could not start the call';
      if (/Permission|NotAllowed|Denied|microphone/i.test(message)) {
        setMicDenied(true);
      } else {
        setStartError('Something went wrong. Please check your connection and try again.');
      }
      setScreen('ready');
    }
  }, [start]);

  const handleEndCall = useCallback(() => {
    setScreen('ended');
  }, []);

  const handleRestart = useCallback(() => {
    handleStart();
  }, [handleStart]);

  return (
    <div className="relative flex h-full w-full items-center justify-center">
      <AnimatePresence mode="wait">
        {screen === 'ready' && (
          <MotionWelcomeView
            key="welcome"
            {...VIEW_MOTION_PROPS}
            startButtonText={appConfig.startButtonText}
            onStartCall={handleStart}
          />
        )}

        {screen === 'connecting' && (
          <MotionConnectingView key="connecting" {...VIEW_MOTION_PROPS} />
        )}

        {screen === 'session' && (
          <MotionSessionView
            key="session"
            {...VIEW_MOTION_PROPS}
            supportsChatInput={appConfig.supportsChatInput}
            audioVisualizerColor={
              resolvedTheme === 'dark'
                ? appConfig.audioVisualizerColorDark
                : appConfig.audioVisualizerColor
            }
            audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
            className="fixed inset-0"
            micPermissionDenied={micDenied}
            onMicPermissionDenied={() => setMicDenied(true)}
            onDismissMicError={() => setMicDenied(false)}
            onEndCall={handleEndCall}
          />
        )}

        {screen === 'ended' && (
          <MotionEndedView key="ended" {...VIEW_MOTION_PROPS} onRestart={handleRestart} />
        )}
      </AnimatePresence>

      {/* Ready-state mic error (before session mounts) */}
      {screen === 'ready' && micDenied && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 px-4 backdrop-blur-sm">
          <MicPermissionBanner
            open
            onDismiss={() => setMicDenied(false)}
            onRetry={handleStart}
          />
        </div>
      )}

      {screen === 'ready' && startError && !micDenied && (
        <div className="absolute inset-x-4 bottom-8 z-40 rounded-2xl border border-foreground/15 bg-background p-4 text-center sm:inset-x-auto sm:bottom-12 sm:w-full sm:max-w-md">
          <p className="font-hand text-base text-foreground">{startError}</p>
        </div>
      )}
    </div>
  );
}
