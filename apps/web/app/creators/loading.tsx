import { Bone, ListBone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="5xl" title="15rem">
      {/* The filter row, then the Creator / Reach / Rate column
          headings above the list. */}
      <Bone className="mt-6 h-[38px] w-full max-w-[26rem] rounded-lg" />

      <div className="mt-7 flex items-baseline gap-4 border-b border-line pb-2">
        <Bone className="h-3 w-16 flex-1 rounded" />
        <Bone className="h-3 w-20 rounded sm:w-24" />
        <Bone className="h-3 w-24 rounded sm:w-28" />
      </div>

      <ListBone rows={6} right="6rem" />
    </PageBone>
  );
}
