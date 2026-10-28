import { Bone, ListBone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="3xl" title="12rem">
      {/* The Inbox / Requests tabs. */}
      <nav className="mt-6 flex items-baseline gap-6 border-b border-line pb-3">
        <Bone className="h-3 w-14 rounded" />
        <Bone className="h-3 w-20 rounded" />
      </nav>

      {/* Shorter rows than a retainer, and the right-hand side is
          a timestamp rather than an amount. */}
      <ListBone rows={6} tall={false} right="3rem" />
    </PageBone>
  );
}
