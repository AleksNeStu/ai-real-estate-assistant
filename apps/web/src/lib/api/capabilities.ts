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
    default_provider: string;
  };
  observability: {
    error_tracking: boolean;
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
