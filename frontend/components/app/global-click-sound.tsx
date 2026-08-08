'use client';

import { useEffect } from 'react';

export function GlobalClickSound() {
  useEffect(() => {
    // Web Audio API is the ONLY way to achieve true 0 latency on the web
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    const audioCtx = new AudioContext();
    let clickBuffer: AudioBuffer | null = null;

    // Pre-fetch and decode the audio file into memory immediately on load
    fetch('/click.mp3')
      .then(response => response.arrayBuffer())
      .then(arrayBuffer => audioCtx.decodeAudioData(arrayBuffer))
      .then(decodedAudio => {
        clickBuffer = decodedAudio;
      })
      .catch(err => console.warn('Failed to load click sound', err));

    const playPencilTap = () => {
      if (!clickBuffer) return; // Wait until loaded

      try {
        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }

        // Create a new source node (this is instant and perfectly overlaps)
        const source = audioCtx.createBufferSource();
        source.buffer = clickBuffer;

        const gainNode = audioCtx.createGain();
        gainNode.gain.value = 0.5; // Volume (0.0 to 1.0)

        source.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        // Start playback with 0 delay
        source.start(0);
      } catch (err) {
        console.warn('Audio click failed', err);
      }
    };

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      // Play sound when clicking interactive pencil elements
      if (
        target.closest('button') || 
        target.closest('a') || 
        target.closest('.pencil-box') || 
        target.closest('.pencil-circle') ||
        target.closest('[role="button"]')
      ) {
        playPencilTap();
      }
    };

    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  return null;
}
