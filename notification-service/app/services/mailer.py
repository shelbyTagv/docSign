"""
notification-service/app/services/mailer.py

HTML email delivery using aiosmtplib (async SMTP).
All email templates are professional HTML — plain text fallback included
for email clients that don't support HTML.

Why aiosmtplib instead of smtplib?
aiosmtplib is the async equivalent of smtplib, compatible with FastAPI's
event loop. Using sync smtplib in an async endpoint would block the event
loop and degrade throughput for all concurrent requests.
"""

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
import os

from ..config import settings


async def send_email(
    to: List[str],
    subject: str,
    html_body: str,
    plain_body: str = "",
    attachment_path: Optional[str] = None,
    attachment_filename: Optional[str] = None
) -> bool:
    """
    Send an email via SMTP with optional PDF attachment.
    Returns True on success, False on failure.
    
    We catch all exceptions and return False (instead of raising) because
    email delivery failures should never crash the document workflow.
    The calling service handles retry/fallback logic.
    """
    if not settings.SMTP_USER or settings.SMTP_USER == "your-email@gmail.com":
        # Log instead of fail if SMTP not configured — development convenience
        print(f"[mailer] SMTP not configured. Would send to {to}: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject

        msg.attach(MIMEText(plain_body or _strip_html(html_body), "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Attach PDF if provided — verify file exists before attempting
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                pdf_data = f.read()
            part = MIMEBase("application", "pdf")
            part.set_payload(pdf_data)
            encoders.encode_base64(part)
            filename = attachment_filename or os.path.basename(attachment_path)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASS,
            use_tls=False,      # Port 587 uses STARTTLS, not direct TLS
            start_tls=True,
        )
        return True

    except Exception as e:
        print(f"[mailer] Email send failed to {to}: {e}")
        return False


def _strip_html(html: str) -> str:
    """Very basic HTML stripping for plain text fallback."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()


def _base_template(content: str, org_name: str = None) -> str:
    """Wrap email content in a professional HTML template."""
    org = org_name or settings.ORG_NAME
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DocSign Notification</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:#1e3a5f;padding:28px 40px;text-align:center;">
            <p style="margin:0;color:#ffffff;font-size:20px;font-weight:700;letter-spacing:1px;">{org.upper()}</p>
            <p style="margin:4px 0 0;color:#94b4d0;font-size:12px;">Digital Document Management System</p>
          </td>
        </tr>
        <!-- Content -->
        <tr>
          <td style="padding:36px 40px;">
            {content}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 40px;border-top:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0;color:#94a3b8;font-size:11px;">
              This is an automated notification from {org}. Please do not reply to this email.<br>
              &copy; {org} — DocSign Platform
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_signatory_notification(
    to_email: str,
    signatory_name: str,
    document_title: str,
    creator_name: str,
    document_id: str,
    frontend_url: str
) -> bool:
    """Email sent to a signatory when it's their turn to sign."""
    sign_url = f"{frontend_url}/documents/{document_id}/sign"
    content = f"""
    <h2 style="color:#1e3a5f;margin:0 0 8px;">Action Required: Document Awaiting Your Signature</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 24px;">Please review and sign the following document.</p>

    <div style="background:#f8fafc;border-left:4px solid #1e3a5f;padding:16px 20px;border-radius:4px;margin-bottom:24px;">
      <p style="margin:0;font-size:13px;color:#94a3b8;">Document</p>
      <p style="margin:4px 0 0;font-size:16px;font-weight:600;color:#1e293b;">{document_title}</p>
    </div>

    <p style="color:#475569;font-size:14px;">Dear <strong>{signatory_name}</strong>,</p>
    <p style="color:#475569;font-size:14px;">
      <strong>{creator_name}</strong> has sent you a document that requires your digital signature.
      Please log in to the DocSign platform to review the document and apply your signature.
    </p>

    <div style="text-align:center;margin:32px 0;">
      <a href="{sign_url}"
         style="background:#1e3a5f;color:#ffffff;text-decoration:none;padding:14px 32px;
                border-radius:6px;font-size:14px;font-weight:600;display:inline-block;">
        Review & Sign Document
      </a>
    </div>

    <p style="color:#94a3b8;font-size:12px;">
      If the button above doesn't work, copy and paste this URL into your browser:<br>
      <a href="{sign_url}" style="color:#1e3a5f;">{sign_url}</a>
    </p>
    """
    return await send_email(
        to=[to_email],
        subject=f"[Action Required] Document Awaiting Your Signature: {document_title}",
        html_body=_base_template(content)
    )


async def send_completion_notification(
    to_emails: List[str],
    document_title: str,
    pdf_path: Optional[str],
    document_id: str,
    frontend_url: str
) -> bool:
    """Email sent to all parties when document signing is complete, with PDF attached."""
    view_url = f"{frontend_url}/documents/{document_id}"
    content = f"""
    <h2 style="color:#166534;margin:0 0 8px;">✓ Document Signing Complete</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 24px;">All signatures have been collected.</p>

    <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px 20px;border-radius:4px;margin-bottom:24px;">
      <p style="margin:0;font-size:13px;color:#94a3b8;">Document</p>
      <p style="margin:4px 0 0;font-size:16px;font-weight:600;color:#1e293b;">{document_title}</p>
    </div>

    <p style="color:#475569;font-size:14px;">
      The signing process for the above document has been completed successfully.
      The final signed document is attached to this email as a PDF for your records.
    </p>
    <p style="color:#475569;font-size:14px;">
      You can also view the document and its full audit trail on the DocSign platform:
    </p>

    <div style="text-align:center;margin:32px 0;">
      <a href="{view_url}"
         style="background:#166534;color:#ffffff;text-decoration:none;padding:14px 32px;
                border-radius:6px;font-size:14px;font-weight:600;display:inline-block;">
        View Signed Document
      </a>
    </div>
    """
    pdf_filename = f"{document_title.replace(' ', '_')}_Signed.pdf" if document_title else "Signed_Document.pdf"
    return await send_email(
        to=to_emails,
        subject=f"Final Signed Document: {document_title}",
        html_body=_base_template(content),
        attachment_path=pdf_path,
        attachment_filename=pdf_filename
    )


async def send_recall_notification(
    to_emails: List[str],
    document_title: str,
    recalled_by: str,
) -> bool:
    """Email sent when a document is recalled."""
    content = f"""
    <h2 style="color:#9f1239;margin:0 0 8px;">Document Recalled</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 24px;">The following document has been recalled.</p>

    <div style="background:#fff1f2;border-left:4px solid #be123c;padding:16px 20px;border-radius:4px;margin-bottom:24px;">
      <p style="margin:0;font-size:13px;color:#94a3b8;">Document</p>
      <p style="margin:4px 0 0;font-size:16px;font-weight:600;color:#1e293b;">{document_title}</p>
    </div>

    <p style="color:#475569;font-size:14px;">
      <strong>{recalled_by}</strong> has recalled the above document from the signing workflow.
      No further action is required from you. If you have questions, please contact the document creator directly.
    </p>
    """
    return await send_email(
        to=to_emails,
        subject=f"Document Recalled: {document_title}",
        html_body=_base_template(content)
    )


async def send_welcome_email(to_email: str, full_name: str, temp_password: str) -> bool:
    """Welcome email for newly created user accounts."""
    content = f"""
    <h2 style="color:#1e3a5f;margin:0 0 8px;">Welcome to DocSign</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 24px;">Your account has been created.</p>

    <p style="color:#475569;font-size:14px;">Dear <strong>{full_name}</strong>,</p>
    <p style="color:#475569;font-size:14px;">
      Your DocSign platform account has been created by your administrator.
      Please log in with the credentials below and complete your MFA setup.
    </p>

    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:20px;margin:20px 0;">
      <p style="margin:0 0 8px;font-size:13px;color:#64748b;">Email</p>
      <p style="margin:0 0 16px;font-size:15px;font-weight:600;color:#1e293b;">{to_email}</p>
      <p style="margin:0 0 8px;font-size:13px;color:#64748b;">Temporary Password</p>
      <p style="margin:0;font-size:15px;font-weight:600;color:#1e293b;font-family:monospace;">{temp_password}</p>
    </div>

    <p style="color:#dc2626;font-size:13px;font-weight:600;">
      ⚠ You must change your password and set up MFA on your first login.
    </p>
    """
    return await send_email(
        to=[to_email],
        subject="Your DocSign Account Has Been Created",
        html_body=_base_template(content)
    )


async def send_reminder_email(to_email: str, signatory_name: str, document_title: str,
                               document_id: str, frontend_url: str) -> bool:
    """48-hour reminder email if signatory hasn't signed yet."""
    sign_url = f"{frontend_url}/documents/{document_id}/sign"
    content = f"""
    <h2 style="color:#b45309;margin:0 0 8px;">Reminder: Document Awaiting Your Signature</h2>
    <p style="color:#64748b;font-size:14px;margin:0 0 24px;">This document requires your attention.</p>

    <p style="color:#475569;font-size:14px;">Dear <strong>{signatory_name}</strong>,</p>
    <p style="color:#475569;font-size:14px;">
      This is a friendly reminder that the document <strong>"{document_title}"</strong>
      is still awaiting your signature. Please review and sign at your earliest convenience.
    </p>

    <div style="text-align:center;margin:32px 0;">
      <a href="{sign_url}"
         style="background:#b45309;color:#ffffff;text-decoration:none;padding:14px 32px;
                border-radius:6px;font-size:14px;font-weight:600;display:inline-block;">
        Sign Document Now
      </a>
    </div>
    """
    return await send_email(
        to=[to_email],
        subject=f"Reminder: Signature Required — {document_title}",
        html_body=_base_template(content)
    )
