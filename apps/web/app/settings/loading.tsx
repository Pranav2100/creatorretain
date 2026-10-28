import { Bone, ListBone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="3xl" title="11rem">
      {/* The workspace's own details. */}
      <Bone className="mt-6 h-3 w-[21rem] max-w-full rounded" />
      <Bone className="mt-7 h-[38px] w-full rounded-lg" />
      <Bone className="mt-5 h-[38px] w-full rounded-lg" />

      {/* Then the team, which is a list of people and their roles. */}
      <div className="mt-14 border-t border-line pt-8">
        <Bone className="h-5 w-[6rem] rounded" />
        <ListBone rows={4} tall={false} right="5rem" />
      </div>
    </PageBone>
  );
}
