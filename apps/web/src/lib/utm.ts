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
  // The hero carries one outbound link (the studio) and two same-site ones
  // (the instrument and the chips), so the slots are the ones that are
  // actually written down. A slot nobody writes is a number the funnel
  // never sees.
  heroTalk: 'hero_talk',
  chips: 'landing_chips',
  instrument: 'landing_instrument',
  features: 'landing_features',
  exitFork: 'exit_fork',
  exitIssue: 'exit_issue',
  // The hosted tier and the studio are two different destinations: they
  // carry two different campaigns and they are read apart in the funnel.
  // One slot for both would make the two clicks one number.
  exitHosted: 'exit_hosted',
  exitStudio: 'exit_studio',
  exitDiscussion: 'exit_discussion',
  waitlist: 'exit_waitlist',
  studioStrip: 'studio_strip',
  faqAsk: 'faq_ask',
  footer: 'footer',
} as const;

export type LandingSlot = (typeof LANDING_SLOTS)[keyof typeof LANDING_SLOTS];

/**
 * The slots of the surfaces inside the application.
 *
 * The landing has its own set; the pages a visitor reaches from it - the
 * showcase, the chat banner, the leads board - have theirs. A click on one of
 * them is a click of the application, and the medium says so: `app`, not
 * `landing`.
 */
export const APP_SLOTS = {
  showcaseStar: 'showcase_star',
  chatBanner: 'chat_banner',
  leadsNote: 'leads',
} as const;

export type AppSlot = (typeof APP_SLOTS)[keyof typeof APP_SLOTS];

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
