import { createClient } from '@libsql/client';
import { NextResponse } from 'next/server';
import path from 'path';

function getDb() {
  const dbPath = path.resolve(process.cwd(), '../backend/data/mo_saathi.db');
  return createClient({ url: `file:${dbPath}` });
}

function anonId(userId: string): string {
  // Return last 8 chars of room identity — readable, non-PII
  return userId ? userId.slice(-8).toUpperCase() : 'ANON';
}

export async function GET() {
  try {
    const db = getDb();

    // ── Summary aggregates ────────────────────────────────────────────────
    const totals = await db.execute(`
      SELECT
        COUNT(*)                                                      AS total,
        SUM(CASE WHEN outcome = 'successful'  THEN 1 ELSE 0 END)     AS successful,
        SUM(CASE WHEN outcome = 'failed'      THEN 1 ELSE 0 END)     AS failed,
        SUM(CASE WHEN outcome = 'in_progress' THEN 1 ELSE 0 END)     AS in_progress,
        AVG(CASE WHEN duration_sec IS NOT NULL THEN duration_sec END) AS avg_duration,
        AVG(CASE WHEN outcome='successful' AND duration_sec IS NOT NULL
                 THEN duration_sec END)                               AS avg_success_duration,
        SUM(exercise_attempted)                                       AS exercises_attempted
      FROM call_sessions
    `);

    const r         = totals.rows[0];
    const total     = Number(r.total)     || 0;
    const successful = Number(r.successful) || 0;
    const failed    = Number(r.failed)    || 0;
    const inProgress = Number(r.in_progress) || 0;
    const avgDur    = r.avg_duration    != null ? Math.round(Number(r.avg_duration))    : null;
    const avgSucDur = r.avg_success_duration != null ? Math.round(Number(r.avg_success_duration)) : null;
    const exercises = Number(r.exercises_attempted) || 0;
    const rate      = total > 0 ? Math.round(successful / total * 1000) / 10 : 0;

    // ── Daily breakdown — last 14 days ────────────────────────────────────
    const daily = await db.execute(`
      SELECT DATE(started_at)                                       AS day,
             COUNT(*)                                               AS total,
             SUM(CASE WHEN outcome='successful' THEN 1 ELSE 0 END) AS successful,
             SUM(CASE WHEN outcome='failed'     THEN 1 ELSE 0 END) AS failed
      FROM   call_sessions
      WHERE  started_at >= DATE('now', '-13 days')
      GROUP  BY day
      ORDER  BY day ASC
    `);
    const daily_series = daily.rows.map((d) => ({
      date:       d.day       as string,
      total:      Number(d.total)      || 0,
      successful: Number(d.successful) || 0,
      failed:     Number(d.failed)     || 0,
    }));

    // ── Recent calls (last 10, ended only, anonymised) ────────────────────
    const recent = await db.execute(`
      SELECT session_id, user_id, call_type, language,
             outcome, exercise_attempted,
             success_reason, failure_reason,
             started_at, duration_sec
      FROM   call_sessions
      WHERE  outcome != 'in_progress'
      ORDER  BY started_at DESC
      LIMIT  10
    `);
    const recent_calls = recent.rows.map((c) => ({
      session_ref:       (c.session_id as string).slice(-6).toUpperCase(),
      user_ref:          anonId(c.user_id as string),
      call_type:         c.call_type as string,
      language:          c.language  as string,
      outcome:           c.outcome   as string,
      exercise_attempted: Boolean(c.exercise_attempted),
      success_reason:    c.success_reason  as string | null,
      failure_reason:    c.failure_reason  as string | null,
      started_at:        c.started_at as string,
      duration_sec:      c.duration_sec != null ? Number(c.duration_sec) : null,
    }));

    return NextResponse.json({
      total_calls:               total,
      successful_calls:          successful,
      failed_calls:              failed,
      in_progress_calls:         inProgress,
      success_rate:              rate,
      avg_duration_sec:          avgDur,
      avg_success_duration_sec:  avgSucDur,
      exercises_attempted:       exercises,
      daily_series,
      recent_calls,
    });

  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes('no such table')) {
      return NextResponse.json({
        total_calls: 0, successful_calls: 0, failed_calls: 0,
        in_progress_calls: 0, success_rate: 0,
        avg_duration_sec: null, avg_success_duration_sec: null,
        exercises_attempted: 0, daily_series: [], recent_calls: [],
      });
    }
    console.error('[/api/analytics]', err);
    return NextResponse.json(
      { error: 'Analytics temporarily unavailable.' },
      { status: 500 }
    );
  }
}
