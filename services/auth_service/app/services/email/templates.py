"""Reusable transactional email templates.

Templates are plain Python string builders (no templating engine dependency)
that produce provider-agnostic :class:`EmailMessage` objects. A single shared
HTML layout keeps branding consistent; per-email builders supply only the body
content, so new emails reuse the same chrome.
"""

from __future__ import annotations

import html

from app.services.email.base import EmailMessage

_HTML_LAYOUT = """\
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body style="margin:0;padding:0;background-color:#f4f5f7;
               font-family:Arial,Helvetica,sans-serif;color:#1f2933;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background-color:#f4f5f7;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0"
                 cellspacing="0"
                 style="background-color:#ffffff;border-radius:8px;
                        overflow:hidden;max-width:600px;width:100%;">
            <tr>
              <td style="background-color:#1a56db;padding:24px 32px;">
                <h1 style="margin:0;font-size:20px;color:#ffffff;">
                  {app_name}
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;font-size:15px;line-height:1.6;">
                {content}
              </td>
            </tr>
            <tr>
              <td style="padding:24px 32px;background-color:#f9fafb;
                         font-size:12px;color:#6b7280;line-height:1.6;">
                {footer}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _render_layout(*, title: str, app_name: str, content: str, footer: str) -> str:
    return _HTML_LAYOUT.format(
        title=html.escape(title),
        app_name=html.escape(app_name),
        content=content,
        footer=footer,
    )


def build_verification_email(
    *,
    to_email: str,
    recipient_name: str,
    verification_link: str,
    expire_hours: int,
    app_name: str,
    support_email: str,
) -> EmailMessage:
    """Build the account verification email.

    Includes a greeting, a prominent "Verify Email" button, the raw link as a
    fallback, an expiration notice, and support information. All interpolated
    values are HTML-escaped to prevent injection into the markup.
    """
    subject = f"Verify your {app_name} email address"
    safe_name = html.escape(recipient_name)
    safe_app = html.escape(app_name)
    safe_link = html.escape(verification_link, quote=True)
    safe_support = html.escape(support_email)

    content = f"""\
                <p style="margin-top:0;">Hi {safe_name},</p>
                <p>
                  Thanks for signing up for {safe_app}. Please confirm your
                  email address to activate your account.
                </p>
                <p style="text-align:center;margin:32px 0;">
                  <a href="{safe_link}"
                     style="background-color:#1a56db;color:#ffffff;
                            text-decoration:none;padding:12px 28px;
                            border-radius:6px;display:inline-block;
                            font-weight:bold;">
                    Verify Email
                  </a>
                </p>
                <p>
                  If the button does not work, copy and paste this link into
                  your browser:
                </p>
                <p style="word-break:break-all;">
                  <a href="{safe_link}" style="color:#1a56db;">{safe_link}</a>
                </p>
                <p style="color:#6b7280;">
                  This link expires in {expire_hours} hour(s). If it expires,
                  you can request a new verification email.
                </p>
                <p style="color:#6b7280;">
                  If you did not create a {safe_app} account, you can safely
                  ignore this email.
                </p>"""

    footer = f"""\
                Need help? Contact us at
                <a href="mailto:{safe_support}"
                   style="color:#1a56db;">{safe_support}</a>.<br />
                &copy; {safe_app}. All rights reserved."""

    html_body = _render_layout(
        title=subject,
        app_name=app_name,
        content=content,
        footer=footer,
    )

    text_body = (
        f"Hi {recipient_name},\n\n"
        f"Thanks for signing up for {app_name}. Please confirm your email "
        f"address to activate your account by visiting the link below:\n\n"
        f"{verification_link}\n\n"
        f"This link expires in {expire_hours} hour(s). If it expires, you can "
        f"request a new verification email.\n\n"
        f"If you did not create a {app_name} account, you can safely ignore "
        f"this email.\n\n"
        f"Need help? Contact us at {support_email}.\n"
        f"\u2014 {app_name}"
    )

    return EmailMessage(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def build_password_reset_email(
    *,
    to_email: str,
    recipient_name: str,
    reset_link: str,
    expire_hours: int,
    app_name: str,
    support_email: str,
) -> EmailMessage:
    """Build the password reset email.

    Includes a greeting, a prominent reset button, the raw link as a fallback,
    an expiration notice, a security warning, and support information.
    """
    subject = f"Reset your {app_name} password"
    safe_name = html.escape(recipient_name)
    safe_app = html.escape(app_name)
    safe_link = html.escape(reset_link, quote=True)
    safe_support = html.escape(support_email)

    content = f"""\
                <p style="margin-top:0;">Hi {safe_name},</p>
                <p>
                  We received a request to reset the password for your
                  {safe_app} account. Click the button below to choose a new
                  password.
                </p>
                <p style="text-align:center;margin:32px 0;">
                  <a href="{safe_link}"
                     style="background-color:#1a56db;color:#ffffff;
                            text-decoration:none;padding:12px 28px;
                            border-radius:6px;display:inline-block;
                            font-weight:bold;">
                    Reset Password
                  </a>
                </p>
                <p>
                  If the button does not work, copy and paste this link into
                  your browser:
                </p>
                <p style="word-break:break-all;">
                  <a href="{safe_link}" style="color:#1a56db;">{safe_link}</a>
                </p>
                <p style="color:#6b7280;">
                  This link expires in {expire_hours} hour(s). After it expires,
                  you can request a new password reset email.
                </p>
                <p style="color:#b45309;font-weight:bold;">
                  Security notice: If you did not request a password reset,
                  ignore this email. Your password will remain unchanged.
                  Consider contacting support if you are concerned about your
                  account security.
                </p>"""

    footer = f"""\
                Need help? Contact us at
                <a href="mailto:{safe_support}"
                   style="color:#1a56db;">{safe_support}</a>.<br />
                &copy; {safe_app}. All rights reserved."""

    html_body = _render_layout(
        title=subject,
        app_name=app_name,
        content=content,
        footer=footer,
    )

    text_body = (
        f"Hi {recipient_name},\n\n"
        f"We received a request to reset the password for your {app_name} "
        f"account. Visit the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {expire_hours} hour(s). After it expires, you "
        f"can request a new password reset email.\n\n"
        f"Security notice: If you did not request a password reset, ignore "
        f"this email. Your password will remain unchanged. Contact "
        f"{support_email} if you are concerned about your account security.\n\n"
        f"Need help? Contact us at {support_email}.\n"
        f"\u2014 {app_name}"
    )

    return EmailMessage(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )
