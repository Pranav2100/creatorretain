import { ListBone, PageBone } from "@/components/skeleton";

export default function Loading() {
  return (
    <PageBone width="5xl" title="13rem">
      {/* A money column on the right, like the real rows. */}
      <ListBone rows={5} right="7rem" />
    </PageBone>
  );
}
