import { redirect } from "next/navigation";

import { getToken } from "@/lib/session";
import { getWorkspaceContext, landingFor } from "@/lib/workspace";

export default async function Home() {
  const token = await getToken();

  if (!token) {
    redirect("/login");
  }

  const context = await getWorkspaceContext(token);

  redirect(context ? landingFor(context.plan) : "/login");
}
