"""
escalation_mailer.py -- Email escalations via Resend (Day 7)
=============================================================
FROM: mosaathi@swayamjethi.me
TO:   ESCALATION_EMAIL_TO env var

Setup (once):
  1. Add domain swayamjethi.me to resend.com/domains
  2. Add the 3 DNS records Resend shows to your registrar
  3. Set RESEND_API_KEY and ESCALATION_EMAIL_TO in backend/.env

Requires: uv add resend  (already done)
"""

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("escalation_mailer")

FROM_EMAIL = "mosaathi@mail.swayamjethi.me"

_URGENCY_COLOR = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}
_URGENCY_LABEL = {"high": "High Priority", "medium": "Medium Priority", "low": "Low Priority"}


def _build_html(ref_id, student_name, reason, summary, urgency, language, contact_method, contact_info, created_at):
    color = _URGENCY_COLOR.get(urgency, "#d97706")
    label = _URGENCY_LABEL.get(urgency, urgency.title())
    safe_summary = summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_reason  = reason.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_name    = (student_name or "Unknown Student").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_info    = (contact_info or "Not provided").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Mo Saathi Help Request {ref_id}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@700&family=Kalam:wght@400;700&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  body {{
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }}
  .brand-title {{
    font-family: 'Caveat', 'Kalam', 'Georgia', cursive, serif;
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#fafaf8;color:#1c1c1c;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#fafaf8;padding:32px 0;">
  <tr><td align="center">
    <!-- Main Pencil-Box Styled Email Container -->
    <table width="560" cellpadding="0" cellspacing="0" style="background-color:#fafaf8;border:2px solid #1c1c1c;border-radius:6px;max-width:560px;box-shadow:4px 4px 0px 0px #1c1c1c;overflow:hidden;">

      <!-- Brand Header -->
      <tr>
        <td style="background-color:#1c1c1c;padding:24px 32px;border-bottom:2px solid #1c1c1c;">
          <p class="brand-title" style="margin:0;color:#fafaf8;font-size:36px;font-weight:700;line-height:1;letter-spacing:0.02em;">Mo Saathi</p>
          <p style="margin:4px 0 0;color:rgba(250,250,248,0.5);font-size:13px;letter-spacing:0.05em;text-transform:uppercase;">Odia AI Tutor &nbsp;·&nbsp; Human Help Request</p>
        </td>
      </tr>

      <!-- Urgency Banner -->
      <tr>
        <td style="background-color:{color};padding:12px 32px;border-bottom:2px solid #1c1c1c;">
          <p style="margin:0;color:#fafaf8;font-size:13px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;">
            {label} &nbsp;&nbsp;|&nbsp;&nbsp; Ref: <strong>{ref_id}</strong>
          </p>
        </td>
      </tr>

      <!-- Student Card -->
      <tr><td style="padding:28px 32px 0;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="background-color:#f4f4f0;border:2px dashed #1c1c1c;border-radius:6px;padding:18px;">
              <p style="margin:0 0 4px;color:#777;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Student Details</p>
              <p style="margin:0;color:#1c1c1c;font-size:22px;font-weight:700;line-height:1.2;">{safe_name}</p>
              <p style="margin:6px 0 0;color:#555;font-size:13px;">
                Language: <strong>{language.title()}</strong> &nbsp;·&nbsp; 
                Prefers: <strong>{contact_method.replace("_"," ").title()}</strong>
              </p>
              <p style="margin:8px 0 0;padding-top:8px;border-top:1px dashed rgba(28,28,28,0.1);color:#1c1c1c;font-size:13px;">
                <strong>Contact Details:</strong> <span style="font-family:monospace;background:rgba(28,28,28,0.06);padding:2px 6px;border-radius:4px;border:1px solid rgba(28,28,28,0.1);">{safe_info}</span>
              </p>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- Escalation Reason -->
      <tr><td style="padding:20px 32px 0;">
        <p style="margin:0 0 6px;color:#777;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Reason for Escalation</p>
        <p style="margin:0;color:#1c1c1c;font-size:16px;font-weight:700;line-height:1.4;">{safe_reason}</p>
      </td></tr>

      <!-- Summary -->
      <tr><td style="padding:20px 32px 0;">
        <p style="margin:0 0 6px;color:#777;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Summary of Student Session</p>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="background-color:#ffffff;border:2px solid #1c1c1c;border-radius:6px;padding:18px;box-shadow:3px 3px 0px 0px #1c1c1c;">
              <p style="margin:0;color:#2c2c2c;font-size:14px;line-height:1.7;">{safe_summary}</p>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- Next Steps -->
      <tr><td style="padding:20px 32px 28px;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="background-color:#1c1c1c;border:2px solid #1c1c1c;border-radius:6px;padding:18px;box-shadow:3px 3px 0px 0px rgba(0,0,0,0.15);">
              <p style="margin:0 0 8px;color:rgba(250,250,248,0.5);font-size:10px;text-transform:uppercase;letter-spacing:0.1em;font-weight:700;">Suggested Next Steps</p>
              <p style="margin:0;color:#fafaf8;font-size:13px;line-height:1.75;">
                1. Review the details above and prepare relevant material.<br/>
                2. Reach out to the student using their preferred details: <strong>{safe_info}</strong>.<br/>
                3. Update or resolve the case on your Mo Saathi teacher portal.
              </p>
            </td>
          </tr>
        </table>
        <p style="margin:16px 0 0;color:#999;font-size:11px;">Raised: {created_at} &nbsp;·&nbsp; Case Reference: {ref_id}</p>
      </td></tr>

      <!-- Footer Info -->
      <tr>
        <td style="border-top:2px solid #1c1c1c;background-color:#f4f4f0;padding:16px 32px;">
          <p style="margin:0;color:#888;font-size:11px;line-height:1.6;">
            Sent automatically by <strong>Mo Saathi</strong>, an educational voice companion. Please handle student contact details and summaries securely in compliance with privacy guidelines.
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


async def send_escalation_email(
    ref_id: str,
    student_name: str,
    reason: str,
    summary: str,
    urgency: str = "medium",
    language: str = "odia",
    contact_method: str = "phone_call",
    contact_info: str = "",
    created_at: str = "",
) -> bool:
    """
    Send the escalation HTML email via Resend.
    Returns True on success, False on any failure.
    Fails gracefully -- the escalation is still saved to DB regardless.
    """
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    to_email = os.environ.get("ESCALATION_EMAIL_TO", "").strip()

    if not api_key:
        logger.warning("[Mailer] RESEND_API_KEY not set -- email skipped.")
        return False
    if not to_email:
        logger.warning("[Mailer] ESCALATION_EMAIL_TO not set -- email skipped.")
        return False

    try:
        import resend  # noqa: PLC0415

        resend.api_key = api_key
        ts = created_at or datetime.now(timezone.utc).isoformat()
        html = _build_html(ref_id, student_name, reason, summary, urgency, language, contact_method, contact_info, ts)

        params: resend.Emails.SendParams = {
            "from": f"Mo Saathi <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": f"Help Request {ref_id} -- {reason[:60]}",
            "html": html,
        }
        result = resend.Emails.send(params)
        logger.info("[Mailer] Email sent: id=%s ref=%s", result.get("id"), ref_id)
        return True
    except Exception as exc:
        logger.error("[Mailer] Failed for %s: %s", ref_id, exc)
        return False
