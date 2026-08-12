import { createClient } from '@libsql/client';
import { NextResponse } from 'next/server';
import path from 'path';

// Reads escalations from the shared SQLite DB used by the Python backend.
// @libsql/client supports local file:// URLs with no native build required.
function getDb() {
  const dbPath = path.resolve(
    process.cwd(),
    '../backend/data/mo_saathi.db'
  );
  return createClient({ url: `file:${dbPath}` });
}

export async function GET() {
  try {
    const db = getDb();
    const result = await db.execute(
      'SELECT * FROM escalations ORDER BY created_at DESC LIMIT 50'
    );
    const rows = result.rows.map((r) => ({
      ref_id:         r.ref_id as string,
      student_name:   (r.student_name as string) || 'Unknown',
      reason:         r.reason as string,
      summary:        r.summary as string,
      urgency:        r.urgency as string,
      language:       r.language as string,
      contact_method: r.contact_method as string,
      contact_info:   (r.contact_info as string) || '',
      status:         r.status as string,
      email_sent:     Boolean(r.email_sent),
      created_at:     r.created_at as string,
    }));
    return NextResponse.json({ escalations: rows });
  } catch (err: unknown) {
    // Table may not exist yet if no escalations have been raised
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes('no such table')) {
      return NextResponse.json({ escalations: [] });
    }
    console.error('[/api/escalations]', err);
    return NextResponse.json({ error: 'Failed to load escalations' }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const { ref_id } = await request.json();
    if (!ref_id) {
      return NextResponse.json({ error: 'ref_id is required' }, { status: 400 });
    }
    const db = getDb();
    await db.execute({
      sql: 'DELETE FROM escalations WHERE ref_id = ?',
      args: [ref_id],
    });
    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    console.error('[DELETE /api/escalations]', err);
    return NextResponse.json({ error: 'Failed to delete escalation' }, { status: 500 });
  }
}

