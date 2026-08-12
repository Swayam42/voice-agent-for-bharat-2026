"use client";

import { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────
interface Escalation {
  ref_id: string;
  student_name: string;
  reason: string;
  summary: string;
  urgency: 'high' | 'medium' | 'low';
  language: string;
  contact_method: string;
  contact_info: string;
  status: string;
  email_sent: boolean;
  created_at: string;
}

// ─── Urgency helpers ─────────────────────────────────────────────────────────
const URGENCY_COLOR: Record<string, string> = {
  high:   'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300 border-red-300 dark:border-red-900',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-300 dark:border-amber-900',
  low:    'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300 border-green-300 dark:border-green-900',
};
const URGENCY_LABEL: Record<string, string> = {
  high: 'High Priority',
  medium: 'Medium Priority',
  low: 'Low Priority',
};
const STATUS_COLOR: Record<string, string> = {
  open:        'bg-foreground/5 text-foreground/70 border-foreground/10',
  resolved:    'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300 border-green-300',
  in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border-blue-300',
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ─── Card ────────────────────────────────────────────────────────────────────
function EscalationCard({ e, onDelete }: { e: Escalation; onDelete: (ref_id: string) => void }) {
  return (
    <div className="pencil-box relative flex flex-col bg-card p-5 text-left font-hand">
      {/* Delete button top right */}
      <button
        onClick={() => onDelete(e.ref_id)}
        className="absolute right-4 top-4 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-destructive focus:outline-none"
        title="Delete request"
      >
        <Trash2 className="size-4" />
      </button>

      {/* Header row */}
      <div className="mb-3 pr-8 flex flex-wrap items-center gap-2">
        <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold ${URGENCY_COLOR[e.urgency] ?? 'bg-muted border-border text-muted-foreground'}`}>
          {URGENCY_LABEL[e.urgency]}
        </span>
        <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold ${STATUS_COLOR[e.status] ?? 'bg-muted border-border text-muted-foreground'}`}>
          {e.status}
        </span>
        {e.email_sent && (
          <span className="rounded-md border border-border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            emailed
          </span>
        )}
        <span className="font-mono text-xs text-muted-foreground ml-auto">{e.ref_id}</span>
      </div>

      {/* Student */}
      <h2 className="font-display mb-0.5 text-xl font-bold text-foreground">{e.student_name || 'Unknown Student'}</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        {e.language.charAt(0).toUpperCase() + e.language.slice(1)} speaker
        &nbsp;·&nbsp;
        Prefers: {e.contact_method.replace(/_/g, ' ')} ({e.contact_info || 'no details'})
        &nbsp;·&nbsp;
        {timeAgo(e.created_at)}
      </p>

      {/* Reason */}
      <p className="mb-2 text-base font-bold text-foreground">{e.reason}</p>

      {/* Summary */}
      <div className="rounded-lg bg-background/50 p-4 text-sm leading-relaxed text-foreground/80 border border-dashed border-border/80">
        {e.summary}
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function EscalationsPage() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  
  // Custom delete confirmation modal states
  const [deletingEscalation, setDeletingEscalation] = useState<Escalation | null>(null);
  const [confirmIdInput, setConfirmIdInput] = useState('');

  useEffect(() => {
    fetch('/api/escalations')
      .then((r) => r.json())
      .then((data) => {
        setEscalations(data.escalations ?? []);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load escalations. Is the backend running?');
        setLoading(false);
      });
  }, []);

  const handleDeleteTrigger = (ref_id: string) => {
    const item = escalations.find((x) => x.ref_id === ref_id);
    if (item) {
      setDeletingEscalation(item);
      setConfirmIdInput('');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingEscalation) return;
    const ref_id = deletingEscalation.ref_id;
    try {
      const res = await fetch('/api/escalations', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ref_id }),
      });
      if (res.ok) {
        setEscalations((prev) => prev.filter((item) => item.ref_id !== ref_id));
        setDeletingEscalation(null);
        setConfirmIdInput('');
      } else {
        alert('Failed to delete request.');
      }
    } catch {
      alert('Error occurred while deleting request.');
    }
  };

  return (
    <main className="min-h-screen bg-background px-4 pb-16 pt-20">
      {/* Page header */}
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 font-hand text-left">
          <h1 className="font-display text-4xl font-bold text-foreground">
            Help Requests
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Students who need a human teacher — sorted newest first.
          </p>
        </div>

        {loading && (
          <div className="flex items-center gap-2 font-hand text-muted-foreground">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            Loading…
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 font-hand text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && escalations.length === 0 && (
          <div className="pencil-box bg-card p-10 text-center font-hand">
            <p className="font-display text-2xl font-bold text-foreground">No Open Requests</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Mo Saathi hasn&apos;t needed human help yet. All students are learning smoothly.
            </p>
          </div>
        )}

        <div className="space-y-6">
          {escalations.map((e) => (
            <EscalationCard key={e.ref_id} e={e} onDelete={handleDeleteTrigger} />
          ))}
        </div>
      </div>

      {/* Handdrawn Delete Modal Overlay */}
      {deletingEscalation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
          <div className="pencil-box flex w-full max-w-md flex-col bg-card p-6 sm:p-8 font-hand text-left relative animate-in fade-in zoom-in-95 duration-150">
            <h3 className="font-display text-2xl font-bold mb-4 text-foreground">Confirm Deletion</h3>
            <p className="text-sm text-muted-foreground mb-5 leading-relaxed">
              This action permanently deletes the help request. Please type the exact reference ID <span className="font-mono bg-foreground/5 px-2 py-0.5 rounded text-foreground font-bold">{deletingEscalation.ref_id}</span> below to confirm.
            </p>
            
            <input
              type="text"
              value={confirmIdInput}
              onChange={(e) => setConfirmIdInput(e.target.value)}
              placeholder="Type Reference ID..."
              className="pencil-box w-full px-4 py-2.5 mb-6 bg-background text-foreground font-mono text-sm uppercase tracking-wider focus:outline-none"
            />

            <div className="flex w-full flex-col sm:flex-row gap-3">
              <button
                disabled={confirmIdInput.toUpperCase() !== deletingEscalation.ref_id}
                onClick={handleDeleteConfirm}
                className="pencil-box font-hand bg-destructive/10 border-destructive text-destructive font-semibold hover:bg-destructive hover:text-white transition-colors h-11 px-4 text-sm disabled:opacity-40 disabled:cursor-not-allowed ml-auto order-1 sm:order-2 flex items-center justify-center"
              >
                Delete Request
              </button>
              <button
                onClick={() => {
                  setDeletingEscalation(null);
                  setConfirmIdInput('');
                }}
                className="pencil-box font-hand bg-background hover:bg-foreground/5 text-foreground h-11 px-4 text-sm order-2 sm:order-1 flex items-center justify-center"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

