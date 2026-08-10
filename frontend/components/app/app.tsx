'use client';

import { useMemo } from 'react';
import { TokenSource } from 'livekit-client';
import { useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import type { AppConfig } from '@/app-config';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { useDebugMode } from '@/hooks/useDebug';
import { getSandboxTokenSource } from '@/lib/utils';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  // ---------------------------------------------------------------------------
  // Stable student identity — persisted in localStorage across sessions.
  // The backend uses this to recognise returning students and load their profile.
  // ---------------------------------------------------------------------------
  const userId = useMemo(() => {
    if (typeof window === 'undefined') return '';
    const STORAGE_KEY = 'mo_saathi_user_id';
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      // Generate a new UUID-like ID for this browser
      id = 'ms_' + crypto.randomUUID().replace(/-/g, '');
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  }, []);

  const tokenSource = useMemo(() => {
    return typeof process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT === 'string'
      ? getSandboxTokenSource(appConfig)
      : TokenSource.endpoint(`/api/token?userId=${userId}`);
  }, [appConfig, userId]);

  const session = useSession(
    tokenSource,
    appConfig.agentName ? { agentName: appConfig.agentName } : undefined
  );

  return (
    <AgentSessionProvider session={session}>
      <AppSetup />
      <main className="relative h-svh w-full overflow-hidden">
        <ViewController appConfig={appConfig} />
      </main>
      <StartAudioButton
        label="Tap to enable sound"
        className="font-hand fixed bottom-24 left-1/2 z-50 h-12 -translate-x-1/2 rounded-full px-6 text-base shadow-md"
      />
      <Toaster
        icons={{
          warning: <WarningIcon weight="bold" />,
        }}
        position="top-center"
        className="toaster group"
        style={
          {
            '--normal-bg': 'var(--popover)',
            '--normal-text': 'var(--popover-foreground)',
            '--normal-border': 'var(--border)',
          } as React.CSSProperties
        }
      />
    </AgentSessionProvider>
  );
}
