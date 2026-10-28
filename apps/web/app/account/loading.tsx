import { Bone, FormBone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="3xl" title="11rem">
      {/* Your details, then changing your password below it. */}
      <FormBone fields={3} />

      <div className="mt-14 border-t border-line pt-8">
        <Bone className="h-5 w-[11rem] rounded" />
        <FormBone fields={2} />
      </div>
    </PageBone>
  );
}
