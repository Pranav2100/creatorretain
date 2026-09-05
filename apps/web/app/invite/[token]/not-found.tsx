export default function InviteNotFound() {
  return (
    <main className="flex flex-1 items-center justify-center bg-paper px-5 py-16">
      <div className="w-full max-w-[26rem] rounded-[14px] border border-line bg-white px-7 py-8">
        <p className="text-[15px] text-ink">This link does not work</p>
        <p className="mt-2 text-[14px] leading-relaxed text-muted">
          It may have been mistyped, or the invitation may have been
          withdrawn. Ask whoever invited you to send a fresh link.
        </p>
      </div>
    </main>
  );
}
