import { API_URL, ApiError } from "@/lib/api";

export type WorkspaceType = "brand" | "creator" | "agency";

export type Plan =
  | "free"
  | "pro"
  | "business"
  | "managed"
  | "verified";

export type Capability =
  | "browse_creators"
  | "view_creator_profile"
  | "advanced_filters"
  | "contact_creator"
  | "create_retainer"
  | "create_campaign"
  | "campaign_dashboard"
  | "managed_service"
  | "publish_profile"
  | "receive_offers"
  | "verified_badge"
  | "represent_creators";

export type WorkspaceSummary = {
  id: string;
  display_name: string;
  slug: string;
  workspace_type: WorkspaceType;
};

export type PlanState = {
  plan: Plan;
  configured_plan: Plan;
  workspace_type: WorkspaceType;
  capabilities: Capability[];
  limits: {
    discovery_results: number | null;
    active_retainers: number | null;
    represented_creators: number | null;
    team_members: number | null;
  };
};

/**
 * What the signed-in workspace is and what it is allowed to do.
 *
 * Fetched together because every signed-in page needs both, and
 * because the plan is what decides which parts of the page are
 * usable rather than merely visible.
 */
export async function getWorkspaceContext(token: string): Promise<{
  workspace: WorkspaceSummary;
  plan: PlanState;
} | null> {
  const headers = { Authorization: `Bearer ${token}` };

  const [workspaceResponse, planResponse] = await Promise.all([
    fetch(`${API_URL}/workspaces/me`, {
      headers,
      cache: "no-store",
    }),
    fetch(`${API_URL}/workspace-plan`, {
      headers,
      cache: "no-store",
    }),
  ]);

  if (
    workspaceResponse.status === 401 ||
    planResponse.status === 401
  ) {
    return null;
  }

  if (!workspaceResponse.ok || !planResponse.ok) {
    throw new ApiError(
      workspaceResponse.status,
      "Could not load your workspace.",
    );
  }

  return {
    workspace: await workspaceResponse.json(),
    plan: await planResponse.json(),
  };
}


/**
 * Where a workspace belongs when it arrives without a destination.
 *
 * A creator cannot browse discovery, so sending them to the
 * creator list means their first screen after signing in is a
 * refusal. Retainers is where their work actually is.
 */
export function landingFor(plan: PlanState): string {
  return plan.capabilities.includes("browse_creators")
    ? "/creators"
    : "/retainers";
}
