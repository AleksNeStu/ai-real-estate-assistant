import type { ReactNode } from 'react';

import type { LegalDocument } from '@/lib/legal';

/**
 * The renderer of a legal document.
 *
 * One renderer for both pages: a privacy policy and a set of terms are the
 * same shape of thing - a title, a date, and a handful of sections - and a
 * second renderer would be a second place where the two could drift apart.
 */
export function LegalDocumentView({
  document,
  children,
}: {
  document: LegalDocument;
  /** Extra content under the title (a link to the other document, say). */
  children?: ReactNode;
}) {
  return (
    <main className="container mx-auto px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <header className="space-y-2 border-b border-border pb-6">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            {document.title}
          </h1>
          <p className="text-sm text-muted-foreground">
            Last changed {document.updated}
          </p>
          {children}
        </header>

        <div className="space-y-8 py-8">
          {document.sections.map((section) => (
            <section key={section.heading} className="space-y-3">
              <h2 className="text-xl font-semibold tracking-tight text-foreground">
                {section.heading}
              </h2>
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph} className="text-sm leading-relaxed text-muted-foreground">
                  {paragraph}
                </p>
              ))}
              {section.points ? (
                <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                  {section.points.map((point) => (
                    <li key={point}>
                      {point.startsWith('http') ? (
                        <a
                          href={point}
                          className="text-primary underline underline-offset-4"
                          rel="noreferrer noopener"
                          target="_blank"
                        >
                          {point}
                        </a>
                      ) : (
                        point
                      )}
                    </li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}
