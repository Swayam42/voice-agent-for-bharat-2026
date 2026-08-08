export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  // agent dispatch configuration
  agentName?: string;

  // LiveKit Cloud Sandbox configuration
  sandboxId?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Mo Saathi',
  pageTitle: 'Mo Saathi — Your learning friend',
  pageDescription:
    'A calm voice learning companion for students in Odisha. Ask questions, learn simply, stay curious.',

  // Keep the UI focused on voice — no camera or screen share clutter
  supportsChatInput: true,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/murf-logo.svg',
  accent: '#111111',
  logoDark: '/murf-logo-dark.svg',
  accentDark: '#f5f5f5',
  startButtonText: 'Start learning',

  // Minimal black & white bars
  audioVisualizerType: 'bar',
  audioVisualizerColor: '#111111',
  audioVisualizerColorDark: '#f5f5f5',
  audioVisualizerBarCount: 5,

  agentName: process.env.AGENT_NAME ?? undefined,
  sandboxId: undefined,
};
