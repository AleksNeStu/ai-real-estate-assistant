/**
 * The UTM convention of the landing page.
 *
 * Every outbound link carries the same four parts, so a click on the studio
 * strip and a click on the "Talk to the studio" button can be told apart:
 *
 *   utm_source=realty.kittray.com
 *   utm_medium=landing | landing_mobile | app
 *   utm_campaign=oss | propvector | studio
 *   utm_content=<the slot on the page>
 *
 * Same-site links do NOT carry UTMs - a UTM on an internal link would restart
 * the session and break the attribution. They carry `?from=<slot>` instead,
 * and `lib/attribution.ts` reports that slot as a navigation interaction.
 */

export const UTM_SOURCE = 'realty.kittray.com';

export type UtmMedium = 'landing' | 'landing_mobile' | 'app';
export type UtmCampaign = 'oss' | 'propvector' | 'studio';

/** The slots of the landing, in the order they appear. */
export const LANDING_SLOTS = {
  heroSearch: 'hero_search',
  heroAssistant: 'hero_assistant',
  heroStar: 'hero_star',
  chips: 'landing_chips',
  instrument: 'landing_instrument',
  features: 'landing_features',
  exitFork: 'exit_fork',
  exitIssue: 'exit_issue',
  exitHosted: 'exit_card',
  exitStudio: 'exit_card',
  exitDiscussion: 'exit_discussion',
  waitlist: 'exit_waitlist',
  studioStrip: 'studio_strip',
  faqAsk: 'faq_ask',
  footer: 'footer',
} as const;

export type LandingSlot = (typeof LANDING_SLOTS)[keyof typeof LANDING_SLOTS];

/**
 * Build an outbound URL with the campaign parameters attached.
 */
export function withUtm(
  url: string,
  options: { medium: UtmMedium; campaign: UtmCampaign; content: string }
): string {
  const separator = url.includes('?') ? '&' : '?';
  const params = new URLSearchParams({
    utm_source: UTM_SOURCE,
    utm_medium: options.medium,
    utm_campaign: options.campaign,
    utm_content: options.content,
  });
  return `${url}${separator}${params.toString()}`;
}

/**
 * A same-site link with its slot attached. The slot is what the attribution
 * helper reports when the visitor arrives.
 */
export function withSlot(path: string, slot: string): string {
  const separator = path.includes('?') ? '&' : '?';
  return `${path}${separator}from=${encodeURIComponent(slot)}`;
}
