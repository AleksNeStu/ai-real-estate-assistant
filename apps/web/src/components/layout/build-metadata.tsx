'use client';

import { useTranslations } from 'next-intl';

import { useCapabilities } from '@/hooks/useCapabilities';

/**
 * Which build this deployment is running.
 *
 * A caller on the deployment's privileged list sees the commit, the moment
 * the images were built and the run that rolled them onto the server. The
 * backend publishes those to nobody else, so this component has nothing to
 * show for an ordinary visitor - and it shows nothing at all, rather than an
 * empty row.
 *
 * The house style for a build stamp: mono, small, quiet, and everything that
 * names something is a link.
 */
export function BuildMetadata() {
  const t = useTranslations('build');
  const { capabilities } = useCapabilities();
  const build = capabilities?.build;

  if (!build) {
    return null;
  }

  const fields: { label: string; value: string; href?: string }[] = [];
  if (build.built_at) {
    fields.push({ label: t('builtAt'), value: build.built_at });
  }
  if (build.deploy_run_id) {
    fields.push({ label: t('deployRun'), value: build.deploy_run_id, href: build.deploy_url });
  }
  if (build.sha) {
    fields.push({ label: t('commit'), value: build.sha, href: build.commit_url });
  }

  if (fields.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[12px] text-muted-foreground">
      {fields.map((field) => (
        <span key={field.label} className="inline-flex items-center gap-1">
          <span>{field.label}</span>
          {field.href ? (
            <a
              href={field.href}
              target="_blank"
              rel="noreferrer"
              className="text-foreground underline underline-offset-4 hover:no-underline"
            >
              {field.value}
            </a>
          ) : (
            <span>{field.value}</span>
          )}
        </span>
      ))}
    </div>
  );
}
