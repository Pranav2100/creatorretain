from html import escape

from app.core.settings import settings
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.services.email.base import EmailMessage

_WRAPPER = """<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f4f4f2;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#f4f4f2;padding:32px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:520px;background:#ffffff;border:1px solid #e6e4de;
              border-radius:12px;font-family:Helvetica,Arial,sans-serif;">
<tr><td style="padding:28px 32px;">
{content}
</td></tr>
<tr><td style="padding:16px 32px;border-top:1px solid #e6e4de;">
<p style="margin:0;font-size:12px;line-height:1.6;color:#8a8781;">{footer}</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _wrap(content: str, footer: str) -> str:
    return _WRAPPER.format(content=content, footer=footer)


def _button(url: str, label: str) -> str:
    return (
        f'<a href="{escape(url)}" '
        'style="display:inline-block;background:#1f1e1c;color:#ffffff;'
        'font-size:15px;font-weight:500;text-decoration:none;'
        'padding:12px 24px;border-radius:8px;">'
        f"{escape(label)}</a>"
    )


def _inviter_name(invitation: WorkspaceInvitation) -> str:
    inviter = invitation.inviter

    if inviter is None:
        return "Someone"

    return f"{inviter.first_name} {inviter.last_name}"


def build_invitation_email(
    invitation: WorkspaceInvitation,
) -> EmailMessage:
    workspace = invitation.workspace

    workspace_name = (
        workspace.display_name if workspace else "a workspace"
    )
    inviter_name = _inviter_name(invitation)
    role = invitation.role.value
    expires = invitation.expires_at.strftime("%d %B %Y")
    url = f"{settings.APP_URL}/invite/{invitation.token}"
    app_name = settings.APP_NAME

    subject = f"{inviter_name} invited you to join {workspace_name}"

    content = f"""
<p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#1f1e1c;">
{escape(inviter_name)} has invited you to join
<strong>{escape(workspace_name)}</strong> on {escape(app_name)}
as a {escape(role)}.
</p>
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"
       style="background:#f7f6f3;border-radius:8px;margin:0 0 24px;">
<tr><td style="padding:14px 16px;font-size:13px;color:#5f5e5a;">
Workspace</td>
<td style="padding:14px 16px;font-size:13px;color:#1f1e1c;" align="right">
{escape(workspace_name)}</td></tr>
<tr><td style="padding:0 16px 14px;font-size:13px;color:#5f5e5a;">
Your role</td>
<td style="padding:0 16px 14px;font-size:13px;color:#1f1e1c;" align="right">
{escape(role)}</td></tr>
</table>
<p style="margin:0 0 22px;">{_button(url, "Accept invitation")}</p>
<p style="margin:0 0 6px;font-size:13px;line-height:1.6;color:#5f5e5a;">
This invitation expires on {expires}.
</p>
<p style="margin:0;font-size:13px;line-height:1.6;color:#5f5e5a;">
If the button does not work, paste this into your browser:<br>
<span style="font-size:12px;color:#185fa5;word-break:break-all;">
{escape(url)}</span>
</p>
"""

    text = f"""{inviter_name} has invited you to join {workspace_name} on {app_name} as a {role}.

Accept the invitation:
{url}

This invitation expires on {expires}.

You received this because {inviter_name} entered this address.
If you were not expecting it, you can ignore this email."""

    footer = (
        f"You received this because {escape(inviter_name)} entered "
        "this address. If you were not expecting it, you can ignore "
        "this email."
    )

    return EmailMessage(
        to=invitation.email,
        subject=subject,
        html_body=_wrap(content, footer),
        text_body=text,
    )


def build_resend_request_email(
    invitation: WorkspaceInvitation,
    recipient_email: str,
) -> EmailMessage:
    workspace = invitation.workspace

    workspace_name = (
        workspace.display_name if workspace else "your workspace"
    )
    url = f"{settings.APP_URL}/workspace/invitations"

    subject = f"{invitation.email} asked for a new invitation"

    content = f"""
<p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#1f1e1c;">
<strong>{escape(invitation.email)}</strong> tried to use their
invitation to {escape(workspace_name)}, but it had already expired.
They have asked you to send it again.
</p>
<p style="margin:0 0 22px;">{_button(url, "Review invitations")}</p>
<p style="margin:0;font-size:13px;line-height:1.6;color:#5f5e5a;">
Resending gives them a fresh link valid for another
{settings.INVITATION_TTL_DAYS} days.
</p>
"""

    text = f"""{invitation.email} tried to use their invitation to {workspace_name}, but it had already expired. They have asked you to send it again.

Review your invitations:
{url}"""

    footer = (
        f"You are receiving this because you can manage invitations "
        f"for {escape(workspace_name)}."
    )

    return EmailMessage(
        to=recipient_email,
        subject=subject,
        html_body=_wrap(content, footer),
        text_body=text,
    )
