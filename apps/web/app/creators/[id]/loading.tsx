import { Bone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="5xl" title="20rem">
      <Bone className="mt-4 h-3 w-[13rem] rounded" />

      {/* Reach, rate, categories. */}
      <div className="mt-9 grid grid-cols-2 gap-6 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index}>
            <Bone className="h-3 w-14 rounded" />
            <Bone className="mt-2.5 h-5 w-[5rem] rounded" />
          </div>
        ))}
      </div>

      {/* The bio, then whatever they can do about it. */}
      <div className="mt-10 max-w-[60ch] space-y-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <Bone
            key={index}
            className="h-3 rounded"
            style={{ width: `${96 - index * 11}%` }}
          />
        ))}
      </div>

      <div className="mt-9 flex flex-wrap gap-3">
        <Bone className="h-[42px] w-[10rem] rounded-lg" />
        <Bone className="h-[42px] w-[8rem] rounded-lg" />
      </div>
    </PageBone>
  );
}
