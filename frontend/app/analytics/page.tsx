"use client";

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

// ── Types ──────────────────────────────────────────────────────────────────────
interface RecentCall {
  session_ref:       string;
  user_ref:          string;
  call_type:         string;
  language:          string;
  outcome:           'successful' | 'failed' | string;
  exercise_attempted: boolean;
  success_reason:    string | null;
  failure_reason:    string | null;
  started_at:        string;
  duration_sec:      number | null;
}

interface Analytics {
  total_calls:              number;
  successful_calls:         number;
  failed_calls:             number;
  in_progress_calls:        number;
  success_rate:             number;
  avg_duration_sec:         number | null;
  avg_success_duration_sec: number | null;
  exercises_attempted:      number;
  daily_series:             { date: string; total: number; successful: number; failed: number }[];
  recent_calls:             RecentCall[];
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function fmtDuration(sec: number | null): string {
  if (sec == null) return '—';
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Stat card ──────────────────────────────────────────────────────────────────
function StatCard({
  label, value, sub, accent,
}: {
  label: string;
  value: number | string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className={`pencil-box flex flex-col bg-card p-4 sm:p-5 font-hand ${accent ? 'border-foreground/60' : ''}`}>
      <span className="text-[10px] sm:text-xs text-muted-foreground uppercase tracking-wide mb-1 leading-tight">
        {label}
      </span>
      <span className="font-display text-3xl sm:text-4xl font-bold text-foreground leading-none">
        {value}
      </span>
      {sub && (
        <span className="mt-1 text-[10px] sm:text-xs text-muted-foreground leading-tight">
          {sub}
        </span>
      )}
    </div>
  );
}

// ── Progress bar ───────────────────────────────────────────────────────────────
function OutcomeBar({ successful, failed }: { successful: number; failed: number }) {
  const totalCompleted = successful + failed;
  if (totalCompleted === 0) return null;
  
  // Calculate exact percentages based ONLY on completed calls (so it always equals 100%)
  const sPct = (successful / totalCompleted) * 100;
  const fPct = (failed / totalCompleted) * 100;

  return (
    <div className="pencil-box bg-card p-4 sm:p-5 font-hand">
      <h3 className="font-display text-base font-bold text-foreground mb-3">Outcome Breakdown</h3>
      <div className="flex h-6 w-full overflow-hidden rounded-sm border-2 border-foreground/30 relative">
        {sPct > 0 && (
          <div
            className="flex items-center justify-center text-[10px] font-bold text-card bg-foreground/85 transition-all duration-700 hover:opacity-90 cursor-default"
            style={{ width: `${sPct}%` }}
            title={`${successful} Successful`}
          >
            {sPct > 12 ? `${Math.round(sPct)}%` : ''}
          </div>
        )}
        {fPct > 0 && (
          <div
            className="flex items-center justify-center text-[10px] font-bold text-foreground/70 bg-foreground/15 transition-all duration-700 hover:bg-foreground/20 cursor-default"
            style={{ width: `${fPct}%` }}
            title={`${failed} Failed`}
          >
            {fPct > 12 ? `${Math.round(fPct)}%` : ''}
          </div>
        )}
      </div>
      <div className="mt-2 flex gap-4 text-xs text-muted-foreground flex-wrap">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-foreground/85" />
          Successful ({successful})
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-foreground/15 border border-foreground/20" />
          Failed ({failed})
        </span>
      </div>
    </div>
  );
}



// ── Recent activity ────────────────────────────────────────────────────────────
function RecentActivity({ calls }: { calls: RecentCall[] }) {
  if (!calls || calls.length === 0) {
    return (
      <div className="pencil-box bg-card p-5 font-hand text-center text-sm text-muted-foreground">
        No completed calls yet.
      </div>
    );
  }

  return (
    <div className="pencil-box bg-card font-hand overflow-hidden">
      <div className="px-5 pt-4 pb-3 border-b border-border/40">
        <h3 className="font-display text-base font-bold text-foreground">Recent Activity</h3>
      </div>
      <ul className="divide-y divide-border/30">
        {calls.map((c, i) => (
          <li key={i} className="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-foreground/[0.02]">
            {/* Outcome icon */}
            <span
              className={`mt-0.5 flex-shrink-0 text-base leading-none ${
                c.outcome === 'successful' ? 'text-foreground' : 'text-muted-foreground/50'
              }`}
              aria-label={c.outcome}
            >
              {c.outcome === 'successful' ? '✓' : '✕'}
            </span>

            {/* Detail */}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground leading-snug">
                {c.outcome === 'successful'
                  ? 'Learning exercise completed'
                  : 'Session ended before exercise'}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {c.call_type === 'outbound' ? 'Outbound' : 'Browser'} call
                &nbsp;·&nbsp;Session {c.session_ref}
                &nbsp;·&nbsp;{fmtDuration(c.duration_sec)}
              </p>
            </div>

            {/* Time */}
            <span className="flex-shrink-0 text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">
              {timeAgo(c.started_at)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────
export default function AnalyticsPage() {
  const [data, setData]       = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = () => {
    fetch('/api/analytics')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: Analytics) => {
        setData(d);
        setLoading(false);
        setLastRefresh(new Date());
        setError(null);
      })
      .catch(() => {
        setError('Analytics are temporarily unavailable.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 3_000); // 3s for real-time feel
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isEmpty = data && data.total_calls === 0 && data.in_progress_calls === 0 && !error;

  return (
    <main className="min-h-screen bg-background px-4 pb-16 pt-20">
      <div className="mx-auto max-w-2xl">

        {/* ── Page header ──────────────────────────────────────────── */}
        <div className="mb-6 font-hand">
          <h1 className="font-display text-3xl sm:text-4xl font-bold text-foreground">
            Call Analytics
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Is Mo Saathi actually helping students learn?
            {lastRefresh && (
              <span className="ml-2 opacity-60">
                · refreshed {lastRefresh.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>

        {/* ── Nav ──────────────────────────────────────────────────── */}
        <div className="mb-8 flex flex-wrap gap-2 text-sm">
          <Link href="/"
            className="pencil-box px-3 py-1.5 font-hand text-foreground hover:bg-foreground/5 transition-colors">
            ← Home
          </Link>
          <Link href="/escalations"
            className="pencil-box px-3 py-1.5 font-hand text-foreground hover:bg-foreground/5 transition-colors">
            Help Requests
          </Link>
        </div>

        {/* ── Loading ───────────────────────────────────────────────── */}
        {loading && (
          <div className="flex items-center gap-2 font-hand text-muted-foreground">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            Loading analytics…
          </div>
        )}

        {/* ── Error ────────────────────────────────────────────────── */}
        {error && (
          <div className="rounded-xl border border-foreground/20 bg-foreground/5 p-4 font-hand text-sm text-foreground/70">
            {error}
          </div>
        )}

        {/* ── Empty state ───────────────────────────────────────────── */}
        {isEmpty && (
          <div className="pencil-box bg-card p-10 text-center font-hand">
            <p className="font-display text-2xl font-bold text-foreground">No calls yet</p>
            <p className="mt-2 text-sm text-muted-foreground max-w-xs mx-auto leading-relaxed">
              Complete your first learning session with Mo Saathi to see analytics here.
            </p>
            <Link href="/"
              className="pencil-box mt-6 inline-block px-5 py-2 text-sm font-hand text-foreground hover:bg-foreground/5 transition-colors">
              Start a session →
            </Link>
          </div>
        )}

        {/* ── Dashboard ─────────────────────────────────────────────── */}
        {data && !error && (data.total_calls > 0 || data.in_progress_calls > 0) && (
          <div className="space-y-4 sm:space-y-5">

            {/* Primary metric cards: Total = Successful + Failed + In Progress */}
            <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:grid-cols-4">
              <StatCard
                label="Total Calls"
                value={data.successful_calls + data.failed_calls + data.in_progress_calls}
                sub="all time"
              />
              <StatCard label="Successful"   value={data.successful_calls}
                        sub="exercise completed" accent />
              <StatCard label="Failed"       value={data.failed_calls}
                        sub="no exercise done" />
              <StatCard
                label="Live Now"
                value={data.in_progress_calls}
                sub={data.in_progress_calls > 0 ? 'in session' : 'no active calls'}
              />
            </div>

            <div className="w-full">
              {/* Outcome breakdown bar */}
              <OutcomeBar
                successful={data.successful_calls}
                failed={data.failed_calls}
              />
            </div>

            {/* Secondary metrics */}
            {(data.avg_duration_sec != null || data.exercises_attempted > 0) && (
              <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3">
                {data.avg_duration_sec != null && (
                  <StatCard label="Avg Call Duration"
                            value={fmtDuration(data.avg_duration_sec)}
                            sub="all calls" />
                )}
                {data.avg_success_duration_sec != null && (
                  <StatCard label="Avg Successful Call"
                            value={fmtDuration(data.avg_success_duration_sec)}
                            sub="exercises completed" />
                )}
                {data.exercises_attempted > 0 && (
                  <StatCard label="Exercises Attempted"
                            value={data.exercises_attempted}
                            sub={`completion rate ${data.total_calls > 0 ? Math.round((data.exercises_attempted / data.total_calls) * 100) : 0}%`} />
                )}
              </div>
            )}

            {/* Recent activity */}
            <RecentActivity calls={data.recent_calls} />

            {/* Success definition (always visible) */}
            <div className="pencil-box bg-card p-4 sm:p-5 font-hand text-sm opacity-80 hover:opacity-100 transition-opacity">
              <h3 className="font-display font-bold text-foreground mb-1">
                What counts as success?
              </h3>
              <p className="text-muted-foreground leading-relaxed">
                A call is <strong className="text-foreground">successful</strong> when the student reaches and attempts at least one practice exercise (the <span className="font-mono text-[10px] bg-foreground/8 rounded px-1">get_next_exercise</span> tool is called). Calls that end before any exercise are <strong className="text-foreground">failed</strong>.
              </p>
            </div>

          </div>
        )}
      </div>
    </main>
  );
}
