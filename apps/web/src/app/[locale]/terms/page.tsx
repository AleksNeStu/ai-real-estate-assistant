import type { Metadata } from 'next';

import { LegalDocumentView } from '@/components/legal/legal-document';
import { TERMS } from '@/lib/legal';
import { pageMetadata } from '@/lib/metadata';

/**
 * /<locale>/terms — the terms of use of the deployment.
 *
 * The second of the two documents the Google consent screen asks for. The
 * text is English on purpose - see the note in `@/lib/legal`.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: TERMS.title,
    description: TERMS.description,
    ...pageMetadata(locale, '/terms'),
  };
}

export default async function TermsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <LegalDocumentView document={TERMS}>
      <p className="text-sm text-muted-foreground">
        What the deployment stores is on the{' '}
        <a
          href={`/${locale}/privacy`}
          className="text-primary underline underline-offset-4"
        >
          privacy policy page
        </a>
        .
      </p>
    </LegalDocumentView>
  );
}
