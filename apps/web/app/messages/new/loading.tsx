import { Bone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="2xl" title="14rem">
      <Bone className="mt-5 h-3 w-[20rem] max-w-full rounded" />
      <Bone className="mt-7 h-[120px] w-full rounded-lg" />
      <Bone className="mt-4 h-[42px] w-[11rem] rounded-lg" />
    </PageBone>
  );
}
