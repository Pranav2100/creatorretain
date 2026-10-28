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

export type WorkspaceRole =
  | "owner"
  | "admin"
  | "manager"
  | "member";

/**
 * How senior a role is. Every question about who may act on whom
 * is a comparison of two of these, which is why it is a number
 * rather than a list of pairs.
 */
export const RANK: Record<WorkspaceRole, number> = {
  member: 0,
  manager: 1,
  admin: 2,
  owner: 3,
};

export const ROLE_LABEL: Record<WorkspaceRole, string> = {
  owner: "Owner",
  admin: "Admin",
  manager: "Manager",
  member: "Member",
};

export type WorkspaceSummary = {
  id: string;
  display_name: string;
  slug: string;
  workspace_type: WorkspaceType;
  your_role: WorkspaceRole;
  verification_status: string;
  legal_name: string | null;
  bio: string | null;
  logo_url: string | null;
  banner_url: string | null;
  website_url: string | null;
};

/** Owners and admins may rewrite the workspace; members may not. */
/**
 * Whether this role may change the workspace itself - its page,
 * its team, who runs which account. A Manager runs accounts but
 * does not run the company, so this is false for them.
 */
export function canEdit(role: WorkspaceRole): boolean {
  return role === "owner" || role === "admin";
}

/**
 * Whether this role sees every retainer the workspace has, or
 * only the ones put in their hands.
 */
export function seesEveryRetainer(role: WorkspaceRole): boolean {
  return role !== "manager";
}

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
export const NO_WORKSPACE = "no-workspace" as const;

export type WorkspaceContext = {
  workspace: WorkspaceSummary;
  plan: PlanState;
};

export async function getWorkspaceContext(
  token: string,
): Promise<WorkspaceContext | typeof NO_WORKSPACE | null> {
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

  // Signed in, but nothing set up yet. Told apart from an expired
  // token because the remedy is completely different: one needs a
  // workspace, the other needs a password.
  if (workspaceResponse.status === 404) {
    return NO_WORKSPACE;
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
