import { Fragment, createElement, type ReactNode } from 'react';
import { ExternalLink } from 'lucide-react';

import { cn } from '@/lib/utils';
import { inspectHref, parseMarkdown, type MdBlock, type MdInline } from './markdown';

/**
 * The answer, drawn as the document the model wrote.
 *
 * The answer is untrusted text: it comes from a model that reads the open
 * web. It is therefore parsed into a tree of nodes and rendered from that
 * tree, never handed to the browser as markup - so a `<script>` in the answer
 * is a paragraph of text, and a `javascript:` destination is a word.
 *
 * The drawing is the app's own: Geist for prose, Geist Mono for code, the
 * type scale of `globals.css`, the zinc chrome, hairline rules and one teal
 * action left to the page. A heading is a heading, a list is a list, and
 * nothing in the answer wears a stock theme.
 */

/** The size of a heading, by the level the model wrote it at. */
const HEADING_CLASS: Record<number, string> = {
  1: 'text-title',
  2: 'text-h3',
  3: 'text-lede',
  4: 'text-body',
  5: 'text-app',
  6: 'text-annot',
};

/** One step of the outline the answer builds. */
interface OutlineEntry {
  /** The level the model wrote. */
  markdownLevel: number;
  /** The level the heading is drawn at. */
  htmlLevel: number;
}

/**
 * The level a heading is drawn at.
 *
 * The answer is a section of the page: the route keeps the one `h1`, so the
 * first heading of an answer is an `h2` and the ones under it step down from
 * there. The model's own level decides the size, this decides the tag, and
 * the outline never skips a level.
 */
function resolveHeadingLevel(markdownLevel: number, outline: OutlineEntry[]): number {
  while (outline.length > 0 && outline[outline.length - 1].markdownLevel > markdownLevel) {
    outline.pop();
  }

  const top = outline[outline.length - 1];
  let htmlLevel: number;
  if (!top) htmlLevel = 2;
  else if (markdownLevel > top.markdownLevel) htmlLevel = top.htmlLevel + 1;
  else htmlLevel = top.htmlLevel;

  htmlLevel = Math.min(htmlLevel, 6);
  outline.push({ markdownLevel, htmlLevel });
  return htmlLevel;
}

export interface MarkdownMessageProps {
  /** The model's answer. Untrusted: parsed, never trusted. */
  children: string;
  className?: string;
}

/** The answer, rendered as markdown. */
export function MarkdownMessage({ children, className }: MarkdownMessageProps) {
  const blocks = parseMarkdown(children);
  const outline: OutlineEntry[] = [];

  return (
    <div
      className={cn(
        'flex flex-col gap-3 break-words text-app leading-relaxed text-foreground',
        className
      )}
    >
      {renderBlocks(blocks, 'answer', outline)}
    </div>
  );
}

export interface PlainMessageProps {
  /** The words, as words. */
  children: string;
  className?: string;
}

/**
 * The words, as words.
 *
 * The error path carries the apology into the same place the answer goes, but
 * it is not a document: it is a sentence about a failure, and it is rendered
 * as plain text so that it can carry no markup at all.
 */
export function PlainMessage({ children, className }: PlainMessageProps) {
  return (
    <p
      className={cn(
        'm-0 whitespace-pre-wrap break-words text-app leading-relaxed text-foreground',
        className
      )}
    >
      {children}
    </p>
  );
}

function renderBlocks(
  blocks: MdBlock[],
  key: string,
  outline: OutlineEntry[]
): ReactNode[] {
  return blocks.map((block, index) => renderBlock(block, `${key}-${index}`, outline));
}

function renderBlock(block: MdBlock, key: string, outline: OutlineEntry[]): ReactNode {
  switch (block.type) {
    case 'heading': {
      const level = resolveHeadingLevel(block.level, outline);
      return createElement(
        `h${level}`,
        {
          key,
          className: cn(
            'mb-0 mt-1.5 font-semibold text-foreground first:mt-0',
            HEADING_CLASS[block.level]
          ),
        },
        renderInlines(block.children, key)
      );
    }

    case 'paragraph':
      return (
        <p key={key} className="m-0 text-app leading-relaxed text-foreground">
          {renderInlines(block.children, key)}
        </p>
      );

    case 'code':
      return (
        <pre
          key={key}
          className="m-0 overflow-x-auto rounded-md border border-border bg-muted/40 p-3 font-mono text-app leading-relaxed text-foreground"
        >
          <code>{block.value}</code>
        </pre>
      );

    case 'list': {
      const items = block.items.map((item, index) => (
        <li key={`${key}-${index}`} className="m-0">
          {renderBlocks(item, `${key}-${index}`, outline)}
        </li>
      ));

      return block.ordered ? (
        <ol
          key={key}
          start={block.start}
          className="m-0 list-decimal space-y-1.5 pl-5 text-app leading-relaxed text-foreground"
        >
          {items}
        </ol>
      ) : (
        <ul
          key={key}
          className="m-0 list-disc space-y-1.5 pl-5 text-app leading-relaxed text-foreground"
        >
          {items}
        </ul>
      );
    }

    case 'quote':
      return (
        <blockquote
          key={key}
          className="m-0 border-l border-border pl-3.5 text-app leading-relaxed text-muted-foreground"
        >
          {renderBlocks(block.children, key, outline)}
        </blockquote>
      );

    case 'rule':
      return <hr key={key} className="border-t border-border" />;
  }
}

function renderInlines(nodes: MdInline[], key: string): ReactNode[] {
  return nodes.map((node, index) => renderInline(node, `${key}-${index}`));
}

function renderInline(node: MdInline, key: string): ReactNode {
  switch (node.type) {
    case 'text':
      return <Fragment key={key}>{node.value}</Fragment>;

    case 'strong':
      return (
        <strong key={key} className="font-semibold text-foreground">
          {renderInlines(node.children, key)}
        </strong>
      );

    case 'emphasis':
      // The house style has no italic: the weight carries the emphasis.
      return (
        <em key={key} className="not-italic font-medium">
          {renderInlines(node.children, key)}
        </em>
      );

    case 'code':
      return (
        <code
          key={key}
          className="rounded-[3px] bg-muted px-1 py-0.5 font-mono text-[13px] text-foreground"
        >
          {node.value}
        </code>
      );

    case 'link': {
      const verdict = inspectHref(node.href);
      if (!verdict.safe) {
        // A destination the browser would execute stays text.
        return <Fragment key={key}>{renderInlines(node.children, key)}</Fragment>;
      }

      return (
        <a
          key={key}
          href={node.href}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
        >
          {renderInlines(node.children, key)}
          {verdict.external ? (
            <ExternalLink aria-hidden="true" className="ml-0.5 inline size-3 align-[-0.125em]" />
          ) : null}
        </a>
      );
    }

    case 'break':
      return <br key={key} />;
  }
}
