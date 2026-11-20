import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Real Estate Assistant',
  description: 'Next-gen real estate search and analytics',
};

/**
 * Root layout - redirects to locale-specific layout.
 * The actual layout with navigation and providers is in [locale]/layout.tsx
 *
 * THE MEASUREMENT
 *   A public site with no measurement is a site nobody can improve: there is
 *   no way to tell whether a change helped. The beacon below is Cloudflare
 *   Web Analytics - it is cookieless, it collects no personal data, and it
 *   reports to the zone this site is served from.
 *
 *   The token is read from the RUNTIME environment, not from a `NEXT_PUBLIC_`
 *   variable: `NEXT_PUBLIC_*` is inlined when the image is built, and the
 *   token belongs to the deployment, not to the build.
 *
 *   Cloudflare's automatic injection does not reach this site: every response
 *   comes through a Worker, and the automatic injection never touches a
 *   Worker response. The beacon has to be in the page.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const analyticsToken = process.env.CF_WEB_ANALYTICS_TOKEN;

  return (
    <>
      {children}
      {analyticsToken ? (
        <script
          defer
          src="https://static.cloudflareinsights.com/beacon.min.js"
          data-cf-beacon={JSON.stringify({ token: analyticsToken })}
        />
      ) : null}
    </>
  );
}
