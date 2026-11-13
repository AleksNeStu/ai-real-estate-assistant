/**
 * The legal pages of the deployment.
 *
 * WHY THE TEXT LIVES HERE AND NOT IN THE MESSAGE CATALOGUE
 *
 * The catalogue carries the interface in nine languages. A legal document is
 * a different thing: it is one text, written once, that the operator can
 * point at, that does not drift between the languages, and that says what
 * the deployment actually does. A translated privacy policy is nine claims
 * about a server that only exists once - and the second translation is the
 * one that will be wrong.
 *
 * So the text is English, on purpose, and it is honest: it names the fields
 * that are stored, where they are stored and who can read them. The pages
 * are reachable at /<locale>/privacy and /<locale>/terms, because the
 * middleware prefixes every path with a locale.
 *
 * The consent screen of the Google sign-in asks for a privacy policy and a
 * terms of service before the app can be published to the public - these are
 * those two pages.
 */

/** One section of a legal document. */
export interface LegalSection {
  /** The heading of the section. */
  heading: string;
  /** The paragraphs of the section, in order. */
  paragraphs: string[];
  /** An optional list of points, under the paragraphs. */
  points?: string[];
}

/** A legal document: a title, a description, a date and its sections. */
export interface LegalDocument {
  /** The title of the page - also the title in the browser and in the metadata. */
  title: string;
  /** The one-line description of the page, used in the metadata. */
  description: string;
  /** The date the text was last changed. */
  updated: string;
  /** The sections, in the order they are read. */
  sections: LegalSection[];
}

/** The privacy policy of the deployment. */
export const PRIVACY: LegalDocument = {
  title: 'Privacy policy',
  description:
    'What this deployment stores when you sign in, where it stores it, and who can read it.',
  updated: '12 November 2026',
  sections: [
    {
      heading: 'What this site is',
      paragraphs: [
        'This site is a public demonstration of AI Real Estate Assistant, an open-source project. It runs the project’s own code on the operator’s server, with a seeded catalogue of listings.',
        'It is free, it is not a commercial offer, and it can be reset, moved or taken down at any time.',
      ],
    },
    {
      heading: 'What is stored when you sign in',
      paragraphs: [
        'If you sign in with Google, the deployment stores the fields Google hands over: your email address, your name, your profile picture, and a link to the Google account that signed in. It also stores the session itself - the tokens, the date of the last sign-in, and the address the sign-in came from.',
        'If you do not sign in, no account is created. The server still keeps short-lived request logs, including the address the request came from, for rate limiting and for diagnosing faults.',
      ],
    },
    {
      heading: 'What you create yourself',
      paragraphs: [
        'Favourites, saved searches, uploaded documents and the questions you ask are stored against your account, because that is how the site can show them back to you.',
      ],
    },
    {
      heading: 'The buyer memory',
      paragraphs: [
        'When you are signed in, the assistant can keep a memory of what you have told it about your search: a budget, areas you ruled out, a feature you need, a listing you liked. It exists so you do not have to repeat yourself on every visit.',
        'The memory belongs to your signed-in account. It is not attached to visitors who are not signed in, and it is not shared between accounts.',
        'The memory is read back into the answers the assistant gives you, so that you do not have to repeat what you said.',
        'The memory stays in the same database as the rest of your account data, on the operator’s own infrastructure. No third party receives it, and no new sub-processor is involved.',
      ],
      points: [
        'How long it is kept: a fact is kept for a year after it is recorded, and then it expires and is removed.',
        'How to delete it: the signed-in account can delete the whole memory at any time, through the account endpoint /api/v1/me/buyer-memory, and deleting your account removes it with the account.',
      ],
    },
    {
      heading: 'Where it is stored',
      paragraphs: [
        'In a database on the server that runs the deployment, on the operator’s own infrastructure. The session cookies are httpOnly: the JavaScript of a page cannot read them.',
      ],
    },
    {
      heading: 'Who can read it',
      paragraphs: [
        'The operator of the deployment can read the account data, because the operator runs the server. Nobody else. The data is not sold, not shared with advertisers, and not used to train models.',
      ],
    },
    {
      heading: 'The Google sign-in itself',
      paragraphs: [
        'The sign-in is carried out by Google, under Google’s own privacy policy. The deployment receives only the fields listed above.',
      ],
    },
    {
      heading: 'How long it is kept',
      paragraphs: [
        'Account data lives as long as the account does. The deployment is a demonstration, and its data may be reset at any time - a reset removes the accounts with it.',
      ],
    },
    {
      heading: 'Your choices',
      paragraphs: [
        'You can ask for your account to be deleted, you can sign out, and you can sign in with a different account. The deployment sends no marketing e-mail and runs no newsletter.',
      ],
    },
    {
      heading: 'Contact',
      paragraphs: [
        'Questions about this page belong in the project’s issue tracker, where they are public and answered in the open.',
      ],
      points: [
        'https://github.com/AleksNeStu/ai-real-estate-assistant/issues',
      ],
    },
  ],
};

/** The terms of use of the deployment. */
export const TERMS: LegalDocument = {
  title: 'Terms of use',
  description:
    'What this demonstration is, what it is not, and the terms under which it is offered.',
  updated: '12 November 2026',
  sections: [
    {
      heading: 'What this is',
      paragraphs: [
        'This site is a public demonstration of an open-source project, offered free of charge and as it is. It is not a commercial service, and it is not a brokerage.',
      ],
    },
    {
      heading: 'Not professional advice',
      paragraphs: [
        'The prices, valuations, market trends and mortgage figures this site produces are modelled estimates computed from its own catalogue. They can be wrong.',
        'Do not use them to decide a transaction, and check anything that matters with a qualified professional.',
      ],
    },
    {
      heading: 'The catalogue',
      paragraphs: [
        'The listings are sample data, modelled on publicly advertised properties. They may be outdated, incomplete or inaccurate, and a listing here is not an offer to buy, sell or rent anything.',
      ],
    },
    {
      heading: 'Accounts',
      paragraphs: [
        'One account per person. The operator may close an account that is used to abuse the deployment or to attack it or other people’s accounts.',
      ],
    },
    {
      heading: 'The buyer memory',
      paragraphs: [
        'If you sign in, the assistant may keep a memory of what you have told it about your search - a budget, areas you ruled out, a feature you need - and use it to answer you. It belongs to your account, it is kept for a year, and you can delete it at any time through your account - the endpoint /api/v1/me/buyer-memory - or by deleting your account.',
        'The memory is a convenience, not a contract. It does not change what a listing is, what it costs, or what the assistant can be asked to do, and it is not a profile that is sold, shared or used to train a model.',
      ],
    },
    {
      heading: 'Availability',
      paragraphs: [
        'The deployment may be reset, moved, throttled or taken down at any time, without notice and without a commitment to any particular availability.',
      ],
    },
    {
      heading: 'Liability',
      paragraphs: [
        'To the extent the law allows it, the operator is not liable for anything that comes from the use of this demonstration - including decisions made on the basis of what it shows.',
      ],
    },
    {
      heading: 'The code',
      paragraphs: [
        'The project is MIT-licensed and the source is public. The code, its licence and its history are on the project’s repository - the hosted demonstration is a separate, additional thing.',
      ],
    },
    {
      heading: 'Changes',
      paragraphs: [
        'These terms travel with the code: the version that is deployed is the version that applies. They can change with a release.',
      ],
    },
  ],
};
