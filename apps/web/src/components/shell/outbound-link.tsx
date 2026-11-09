'use client';

import type { AnchorHTMLAttributes, ReactNode } from 'react';

import { reportOutbound } from '@/lib/attribution';

/**
 * An outbound link that reports its own click.
 *
 * An outbound click cannot be measured server-side: the browser leaves the
 * site before the request could be counted. The click is therefore reported
 * from the browser, in the click handler, before the navigation happens -
 * `keepalive` lets the request finish on its way out.
 */
export interface OutboundLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  /**
   * What was clicked - the studio name, the campaign, the target.
   *
   * Named `outboundTarget` and not `target`, because `target` is already an
   * HTML attribute of the anchor and the two would collide.
   */
  outboundTarget: string;
  /** The slot on the page the link sits in. */
  slot: string;
  /** The campaign the link belongs to. */
  campaign?: string;
  children: ReactNode;
}

export function OutboundLink({
  outboundTarget,
  slot,
  campaign,
  children,
  onClick,
  ...rest
}: OutboundLinkProps) {
  return (
    <a
      {...rest}
      onClick={(event) => {
        void reportOutbound(outboundTarget, slot, campaign);
        onClick?.(event);
      }}
    >
      {children}
    </a>
  );
}
