import type { Metadata } from 'next';

import { LegalDocumentView } from '@/components/legal/legal-document';
import { PRIVACY } from '@/lib/legal';
import { pageMetadata } from '@/lib/metadata';

/**
 * /<locale>/privacy — the privacy policy of the deployment.
 *
 * The consent screen of the Google sign-in asks for a privacy policy and a
 * terms of service before the app can be published to the public; this is
 * the first of the two.
 *
 * The text is English on purpose - see the note in `@/lib/legal`. The page
 * carries its own title and description (the catalogue does not translate a
 * legal document), and the canonical plus the hreflang map, so the page
 * claims one URL in every language instead of nine.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: PRIVACY.title,
    description: PRIVACY.description,
    ...pageMetadata(locale, '/privacy'),
  };
}

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <LegalDocumentView document={PRIVACY}>
      <p className="text-sm text-muted-foreground">
        The terms of use are on the{' '}
        <a
          href={`/${locale}/terms`}
          className="text-primary underline underline-offset-4"
        >
          terms of use page
        </a>
        .
      </p>
    </LegalDocumentView>
  );
}
