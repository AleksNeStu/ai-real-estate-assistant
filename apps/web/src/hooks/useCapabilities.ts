'use client';

import { useEffect, useState } from 'react';

import { getCapabilities, type DeploymentCapabilities } from '@/lib/api/capabilities';

/**
 * What this deployment can actually do.
 *
 * The answer comes from the backend and it is fetched once per page load and
 * shared by whoever asks. It is the same for every visitor - except the
 * build it carries, which only a caller on the deployment's privileged list
 * is told about. A failure is not an error state: the caller keeps its
 * optimistic rendering and the deployment simply says nothing about itself.
 */
export function useCapabilities(): {
  capabilities: DeploymentCapabilities | null;
  loading: boolean;
} {
  const [capabilities, setCapabilities] = useState<DeploymentCapabilities | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const result = await getCapabilities();
        if (!cancelled) setCapabilities(result);
      } catch {
        // Without the capabilities the deployment promises nothing.
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { capabilities, loading };
}
