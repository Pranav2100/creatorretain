type Props = {
  status: "expired" | "accepted" | "declined" | "cancelled" | "pending";
  workspace: string;
  inviter: string;
};

const COPY: Record<Props["status"], (p: Props) => string> = {
  expired: (p) =>
    `This invitation has passed its date. Ask ${p.inviter} to send a new one and you can join straight away.`,
  accepted: (p) =>
    `You have already joined ${p.workspace}. Sign in to pick up where you left off.`,
  declined: (p) =>
    `You turned this one down. If that was a mistake, ask ${p.inviter} to invite you again.`,
  cancelled: (p) =>
    `${p.inviter} withdrew this invitation. Get in touch with them if you think it was in error.`,
  pending: () => "This invitation is still open.",
};

export function ClosedPanel(props: Props) {
  const heading =
    props.status === "accepted" ? "Already joined" : "No longer open";

  return (
    <div>
      <p className="text-[15px] text-ink">{heading}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-muted">
        {COPY[props.status](props)}
      </p>
    </div>
  );
}
