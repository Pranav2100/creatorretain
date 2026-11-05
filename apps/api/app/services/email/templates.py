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
    app_name = settings.EMAIL_FROM_NAME

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


# ----------------------------------------------------------------------
# Notifications
#
# One builder for every kind, driven off a table rather than a
# chain of ifs. Each entry is a subject line and a sentence; the
# wrapper, the button and the footer are shared, so adding a kind
# is a row here rather than another near-copy of the invitation
# template above.
#
# Rendered at send time from the facts stored on the row, which
# is what lets a wording fix reach everything still queued.
# ----------------------------------------------------------------------

def _retainer_url(payload: dict) -> str:
    return f"{settings.APP_URL}/retainers/{payload.get('retainer_id', '')}"


def _conversation_url(payload: dict) -> str:
    return (
        f"{settings.APP_URL}/messages/"
        f"{payload.get('conversation_id', '')}"
    )


# kind -> (subject, sentence, button label, url builder)
_NOTIFICATIONS: dict[str, tuple[str, str, str, object]] = {
    "offer_received": (
        "You have a new offer: {title}",
        "Somebody wants to put you on a monthly retainer. "
        "Nothing is agreed until you accept it.",
        "Read the offer",
        _retainer_url,
    ),
    "offer_accepted": (
        "{title} was accepted",
        "Your offer was accepted. The first month opens today.",
        "Open the retainer",
        _retainer_url,
    ),
    "offer_declined": (
        "{title} was declined",
        "Your offer was declined. Nothing has been charged.",
        "Open the retainer",
        _retainer_url,
    ),
    "pause_requested": (
        "A pause was asked for on {title}",
        "The other side has asked to pause this retainer. "
        "It keeps running until you agree.",
        "Review the request",
        _retainer_url,
    ),
    "resume_requested": (
        "A restart was asked for on {title}",
        "The other side has asked to start this retainer again.",
        "Review the request",
        _retainer_url,
    ),
    "request_rejected": (
        "Your request on {title} was turned down",
        "The request was turned down, so nothing has changed.",
        "Open the retainer",
        _retainer_url,
    ),
    "paused": (
        "{title} is paused",
        "Both sides agreed, so this retainer is now paused. "
        "Nothing is due while it is.",
        "Open the retainer",
        _retainer_url,
    ),
    "resumed": (
        "{title} is running again",
        "This retainer has started again.",
        "Open the retainer",
        _retainer_url,
    ),
    "notice_given": (
        "Notice was given on {title}",
        "This retainer will end once the notice period is up. "
        "The months until then run as normal.",
        "Open the retainer",
        _retainer_url,
    ),
    "ended": (
        "{title} has ended",
        "This retainer has ended. Nothing further is due.",
        "Open the retainer",
        _retainer_url,
    ),
    "work_submitted": (
        "Work was submitted on {title}",
        "There is something waiting for you to review.",
        "Review the work",
        _retainer_url,
    ),
    "work_approved": (
        "Work was approved on {title}",
        "Your work was approved.",
        "Open the retainer",
        _retainer_url,
    ),
    "changes_requested": (
        "Changes were asked for on {title}",
        "The other side has asked for changes before approving.",
        "Read what was asked",
        _retainer_url,
    ),
    "work_rejected": (
        "Work was rejected on {title}",
        "Something you submitted was rejected.",
        "Open the retainer",
        _retainer_url,
    ),
    "unread_messages": (
        "{from_name} messaged you",
        "You have a message you have not read yet.",
        "Read it",
        _conversation_url,
    ),
    "message_request": (
        "{from_name} wants to message you",
        "Somebody you have not spoken to before would like to "
        "get in touch. Nothing reaches your inbox until you "
        "accept.",
        "See the request",
        _conversation_url,
    ),
    "password_changed": (
        "Your password was changed",
        "Your password was changed just now, and any other "
        "sessions were signed out. If this was not you, reset "
        "your password immediately.",
        "Go to your account",
        lambda payload: f"{settings.APP_URL}/account",
    ),
}


def build_notification_email(notification) -> EmailMessage:
    """
    The email for one queued notification.

    Takes the row rather than the thing that happened, because by
    now the thing that happened may be minutes old or gone - the
    facts it needs were copied onto the row when it was queued.
    """
    payload = notification.payload or {}
    kind = notification.kind.value

    subject_template, sentence, label, url_for = _NOTIFICATIONS[kind]

    # Nothing in a payload is trusted into a subject line beyond
    # what the templates name, and anything missing falls back to
    # wording that still reads.
    fields = {
        "title": payload.get("title") or "your retainer",
        "from_name": payload.get("from_name") or "Somebody",
    }

    subject = subject_template.format(**fields)
    url = url_for(payload)
    note = (payload.get("note") or "").strip()

    quoted = ""

    if note:
        quoted = f"""
<table role="presentation" cellpadding="0" cellspacing="0" width="100%"
       style="background:#f7f6f3;border-radius:8px;margin:0 0 24px;">
<tr><td style="padding:14px 16px;font-size:14px;line-height:1.6;color:#1f1e1c;">
{escape(note)}</td></tr>
</table>
"""

    content = f"""
<p style="margin:0 0 8px;font-size:17px;line-height:1.4;color:#1f1e1c;">
<strong>{escape(subject)}</strong>
</p>
<p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#1f1e1c;">
{escape(sentence)}
</p>
{quoted}
<p style="margin:0 0 22px;">{_button(url, label)}</p>
<p style="margin:0;font-size:13px;line-height:1.6;color:#5f5e5a;">
If the button does not work, paste this into your browser:<br>
<span style="font-size:12px;color:#185fa5;word-break:break-all;">
{escape(url)}</span>
</p>
"""

    text_note = f"\n\n{note}\n" if note else ""

    text = f"""{subject}

{sentence}{text_note}

{label}:
{url}"""

    if notification.kind.is_security:
        footer = (
            "This one is sent whatever your notification settings "
            "say, because it is about the security of your account."
        )
        text += (
            "\n\nThis one is sent whatever your notification "
            "settings say, because it is about the security of "
            "your account."
        )
    else:
        footer = (
            "You are getting this because of what you are working "
            "on. You can change what we email you about in your "
            "account settings."
        )
        text += (
            "\n\nYou can change what we email you about in your "
            "account settings."
        )

    return EmailMessage(
        to=notification.to_email,
        subject=subject,
        html_body=_wrap(content, footer),
        text_body=text,
    )
