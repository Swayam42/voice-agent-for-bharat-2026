'use client';

import { useEffect, useMemo, useState } from 'react';
import { Track } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import {
  type AgentState,
  useAgent,
  useSessionContext,
  useSessionMessages,
  useVoiceAssistant,
} from '@livekit/components-react';
import { MicIcon, MicOffIcon, PhoneOffIcon, DownloadIcon } from 'lucide-react';
import { AgentAudioVisualizerBar } from '@/components/agents-ui/agent-audio-visualizer-bar';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import { AgentStatus, mapAgentStateToPhase } from '@/components/app/agent-status';
import { MicPermissionBanner } from '@/components/app/mic-permission-banner';
import { Button } from '@/components/ui/button';
import { useInputControls } from '@/hooks/agents-ui/use-agent-control-bar';
import { cn } from '@/lib/shadcn/utils';

interface SessionViewProps {
  audioVisualizerColor?: `#${string}`;
  audioVisualizerBarCount?: number;
  supportsChatInput?: boolean;
  className?: string;
  onMicPermissionDenied?: () => void;
  micPermissionDenied?: boolean;
  onDismissMicError?: () => void;
  onEndCall?: () => void;
}

export function SessionView({
  audioVisualizerColor = '#111111',
  audioVisualizerBarCount = 5,
  supportsChatInput = true,
  className,
  onMicPermissionDenied,
  micPermissionDenied = false,
  onDismissMicError,
  onEndCall,
  ref,
}: React.ComponentProps<'section'> & SessionViewProps) {
  const session = useSessionContext();
  const agent = useAgent();
  const { state: voiceState, audioTrack } = useVoiceAssistant();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const [showExportPrompt, setShowExportPrompt] = useState(false);

  const { microphoneToggle } = useInputControls({
    onDeviceError: ({ source, error }) => {
      if (source === Track.Source.Microphone) {
        console.error('Microphone error', error);
        onMicPermissionDenied?.();
      }
    },
  });

  const agentState = (agent.state ?? voiceState) as AgentState | undefined;
  const phase = mapAgentStateToPhase(agentState);

  const statusPhase = useMemo(() => {
    if (!session.isConnected) return 'connecting' as const;
    if (agentState === 'connecting' || agentState === 'initializing') return 'connecting' as const;
    return phase;
  }, [session.isConnected, agentState, phase]);

  useEffect(() => {
    // Soft auto-open transcript once conversation starts (still optional)
    if (messages.length > 0 && supportsChatInput) {
      // keep closed by default for calm focus — user can open
    }
  }, [messages.length, supportsChatInput]);

  const handleEnd = async () => {
    // Instantly silence the agent locally so it stops speaking during the prompt
    if (audioTrack?.publication?.track?.mediaStreamTrack) {
      audioTrack.publication.track.mediaStreamTrack.enabled = false;
    }

    if (messages && messages.length > 0) {
      setShowExportPrompt(true);
    } else {
      await finalizeEnd();
    }
  };

  const finalizeEnd = async () => {
    onEndCall?.();
    await session.end();
  };

  const handleExportChoice = async (wantExport: boolean) => {
    if (wantExport) {
      let txt = 'Mo Saathi Conversation Transcript\n\n';
      for (const msg of messages) {
        const role = msg.from?.isLocal ? 'You' : 'Mo Saathi';
        txt += `${role}:\n${msg.message}\n\n`;
      }
      const blob = new Blob([txt], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mo_saathi_conversation_${new Date().toISOString().slice(0, 10)}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
    setShowExportPrompt(false);
    await finalizeEnd();
  };

  const handleRetryMic = async () => {
    onDismissMicError?.();
    try {
      if (!microphoneToggle.enabled) {
        await microphoneToggle.toggle(true);
      }
    } catch {
      onMicPermissionDenied?.();
    }
  };

  return (
    <section
      ref={ref}
      className={cn(
        'bg-background relative z-10 flex h-full w-full flex-col overflow-hidden',
        className
      )}
    >
      {/* Top status */}
      <div className="safe-top flex shrink-0 flex-col items-center px-4 pt-6 pb-2 sm:pt-8">
        <p className="font-display mb-3 text-base text-foreground/45">Mo Saathi</p>
        <AgentStatus phase={statusPhase} compact={chatOpen} />
      </div>

      {/* Center visualizer */}
      <div className="relative flex min-h-0 flex-1 flex-col items-center justify-center px-4">
        <AnimatePresence mode="wait">
          {!chatOpen && (
            <motion.div
              key="visualizer"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="flex flex-col items-center"
            >
              <div
                className={cn(
                  'relative flex size-[220px] items-center justify-center sm:size-[280px] transition-transform duration-500 ease-out',
                  statusPhase === 'speaking' && 'scale-75'
                )}
                style={{ color: audioVisualizerColor }}
              >
                <AgentAudioVisualizerBar
                  size="md"
                  state={agentState}
                  color={audioVisualizerColor}
                  audioTrack={audioTrack}
                  barCount={audioVisualizerBarCount}
                  className={cn(
                    "gap-3 transition-all duration-500",
                    statusPhase === 'speaking' ? "h-[80px] w-[140px] sm:h-[100px] sm:w-[160px]" : "h-[120px] w-[180px] sm:h-[140px] sm:w-[200px]"
                  )}
                >
                  <span className="min-h-3 w-3 rounded-full bg-current/15 transition-colors duration-250 ease-linear data-[lk-highlighted=true]:bg-current sm:min-h-3.5 sm:w-3.5" />
                </AgentAudioVisualizerBar>
              </div>

            </motion.div>
          )}
        </AnimatePresence>

        {/* Optional live transcript */}
        {supportsChatInput && chatOpen && (
          <div className="absolute inset-x-0 top-0 bottom-0 mx-auto max-w-lg overflow-hidden px-2">
            <AgentChatTranscript
              agentState={agentState}
              messages={messages}
              className="h-full w-full [&_.is-user>div]:rounded-2xl [&>div>div]:px-3 [&>div>div]:pt-4"
            />
          </div>
        )}
      </div>

      {/* Mic error */}
      {micPermissionDenied && (
        <div className="absolute inset-x-3 top-1/2 z-40 -translate-y-1/2 sm:inset-x-6">
          <MicPermissionBanner
            open
            onDismiss={onDismissMicError}
            onRetry={handleRetryMic}
          />
        </div>
      )}

      {/* Export Prompt Modal */}
      <AnimatePresence>
        {showExportPrompt && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm px-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="pencil-box flex flex-col items-center p-6 sm:p-8 max-w-sm text-center bg-background"
            >
              <DownloadIcon className="size-8 mb-4 text-foreground/80" strokeWidth={1.5} />
              <h3 className="font-hand text-xl font-bold mb-2">Export Conversation?</h3>
              <p className="font-hand text-muted-foreground mb-6">Would you like to save your conversation as a .txt file before leaving?</p>
              <div className="flex w-full gap-3">
                <Button
                  variant="outline"
                  className="pencil-box flex-1 h-12 shadow-none font-hand text-lg bg-background"
                  onClick={() => handleExportChoice(false)}
                >
                  No, thanks
                </Button>
                <Button
                  variant="outline"
                  className="pencil-box flex-1 h-12 shadow-none font-hand text-lg text-black bg-white hover:bg-gray-100"
                  onClick={() => handleExportChoice(true)}
                >
                  Yes, save it
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Bottom controls — large, phone-first */}
      <div className="safe-bottom shrink-0 px-4 pt-2 pb-6 sm:pb-10">
        <div className="mx-auto flex w-full max-w-sm flex-col items-center gap-4">
          <div className="flex w-full items-center justify-center gap-4">
            <Button
              type="button"
              size="lg"
              variant={microphoneToggle.enabled ? 'outline' : 'default'}
              disabled={microphoneToggle.pending}
              onClick={() => microphoneToggle.toggle()}
              aria-label={microphoneToggle.enabled ? 'Mute microphone' : 'Unmute microphone'}
              className="size-16 p-0 shadow-none sm:size-[4.25rem] pencil-circle transition-all"
            >
              {microphoneToggle.enabled ? (
                <MicIcon className="size-6" strokeWidth={1.75} />
              ) : (
                <MicOffIcon className="size-6" strokeWidth={1.75} />
              )}
            </Button>

            <Button
              type="button"
              size="lg"
              variant="outline"
              onClick={handleEnd}
              aria-label="End call"
              className="pencil-box h-16 min-w-[9.5rem] px-6 font-hand text-lg shadow-none sm:h-[4.25rem] sm:min-w-[11rem] sm:text-xl"
            >
              <PhoneOffIcon className="size-5" strokeWidth={1.75} />
              End call
            </Button>
          </div>

          {supportsChatInput && (
            <button
              type="button"
              onClick={() => setChatOpen((v) => !v)}
              className="font-hand text-base text-muted-foreground underline decoration-foreground/20 underline-offset-4 transition-colors hover:text-foreground"
            >
              {chatOpen ? 'Hide notes' : 'Show notes'}
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
