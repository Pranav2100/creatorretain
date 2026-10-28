import { Bone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="3xl" title="16rem">
      <Bone className="mt-4 h-3 w-[10rem] rounded" />

      <div className="mt-9 max-w-[60ch] space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <Bone
            key={index}
            className="h-3 rounded"
            style={{ width: `${94 - index * 14}%` }}
          />
        ))}
      </div>
    </PageBone>
  );
}
