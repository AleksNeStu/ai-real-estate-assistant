/**
 * Deployment capabilities API.
 *
 * The interface must not promise what the deployment cannot do: the sign-in
 * page renders an OAuth button only for a provider the backend says is
 * configured, and the footer states plainly when e-mail is not actually sent.
 */

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

export interface DeploymentCapabilities {
  auth: {
    jwt_enabled: boolean;
    /** True means an anonymous visitor gets a synthetic user. */
    demo_user_bypass: boolean;
    oauth: {
      google: boolean;
      apple: boolean;
    };
  };
  email: {
    /** False means a dummy mail service is in place — nothing is ever sent. */
    enabled: boolean;
    provider: string;
  };
  llm: {
    demo_mode: boolean;
    /** "local-model" means canned answers; "provider" means a real model answers. */
    mode: 'local-model' | 'provider';
    provider: string;
    model: string;
  };
  lead_capture: {
    /** The waitlist may only promise an e-mail when one can be sent. */
    waitlist_enabled: boolean;
  };
  observability: {
    error_tracking: boolean;
  };
  /**
   * The build this deployment is running.
   *
   * Present only for a caller on the deployment's privileged list - the
   * backend publishes it to nobody else, so an ordinary visitor gets no
   * `build` key at all and the interface has nothing to show.
   */
  build?: {
    /** The commit the images were built from. */
    sha?: string;
    /** When the images were built. */
    built_at?: string;
    /** The run that rolled this build onto the server. */
    deploy_run_id?: string;
    /** Where the commit lives. */
    commit_url?: string;
    /** Where the deploy run lives. */
    deploy_url?: string;
  };
}

/**
 * Read what this deployment can actually do.
 *
 * The caller decides what to do when the request itself fails: a network
 * error must not hide the UI, it must only keep the optimistic rendering.
 */
export async function getCapabilities(): Promise<DeploymentCapabilities> {
  const response = await safeFetch(`${getApiUrl()}/capabilities`, {
    method: 'GET',
    headers: {
      ...buildHeaders(),
    },
  });
  return handleResponse<DeploymentCapabilities>(response);
}
