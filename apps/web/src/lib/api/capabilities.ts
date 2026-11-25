/**
 * Deployment capabilities API.
 *
 * The interface must not promise what the deployment cannot do: the sign-in
 * page renders an OAuth button only for a provider the backend says is
 * configured, and the footer states plainly when e-mail is not actually sent.
 *
 * The demo flags are published split - the canned model, the seeded
 * catalogue - because a deployment can answer with a live model and still
 * hold the seeded catalogue. The ingestion keys say what the deployment can
 * read, so a page never offers a file it would refuse.
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
    /**
     * True means the answers come from the canned local model, not from a
     * provider.
     *
     * The master demo flag is not published: it is the fallback of the four
     * split flags, and a deployment that answers with a live model must not
     * read as a demo.
     */
    demo_llm_mode: boolean;
    /** "local-model" means canned answers; "provider" means a real model answers. */
    mode: 'local-model' | 'provider';
    provider: string;
    model: string;
  };
  data: {
    /** True means the catalogue of the deployment is the seeded demo one. */
    demo_data_mode: boolean;
  };
  /**
   * What the deployment can read into the catalogue.
   *
   * The keys are absent when the deployment answers without them, so every
   * reader treats a missing key as "the deployment has not said".
   */
  ingest?: {
    /**
     * The file extensions this deployment can read into the catalogue.
     *
     * A format whose reader is not installed fails at the read, so the
     * interface offers only what the deployment can open.
     */
    formats: string[];
    /** True means a spreadsheet can be read. */
    excel: boolean;
    /**
     * True means this deployment holds the official register, false means it
     * holds none, and null means the deployment could not be asked.
     *
     * The register is read from the sales the ingest stored, so a deployment
     * that stored none of them cannot read it and the interface does not
     * offer it. A deployment that could not be asked is not the same fact as
     * a deployment that holds none, so the answer keeps the difference.
     */
    register: boolean | null;
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
