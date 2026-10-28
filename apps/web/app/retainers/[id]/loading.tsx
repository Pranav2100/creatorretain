import { Bone, CardBone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="5xl" title="18rem">
      {/* Who it is with and what state it is in. */}
      <Bone className="mt-4 h-3 w-[12rem] rounded" />

      {/* The money and dates summary. */}
      <div className="mt-9 grid grid-cols-2 gap-6 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index}>
            <Bone className="h-3 w-16 rounded" />
            <Bone className="mt-2.5 h-5 w-[5.5rem] rounded" />
          </div>
        ))}
      </div>

      {/* Deliverables, then the history underneath. */}
      <div className="mt-10 space-y-3">
        <CardBone lines={2} />
        <CardBone lines={2} />
      </div>

      <Bone className="mt-12 h-5 w-[9rem] rounded" />
      <div className="mt-5 space-y-3.5">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="flex items-baseline gap-3">
            <Bone className="h-3 w-[4.5rem] shrink-0 rounded" />
            <Bone
              className="h-3 rounded"
              style={{ width: `${52 - index * 8}%` }}
            />
          </div>
        ))}
      </div>
    </PageBone>
  );
}
