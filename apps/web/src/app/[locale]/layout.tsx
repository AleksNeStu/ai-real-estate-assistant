import type { Metadata, Viewport } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations, setRequestLocale } from 'next-intl/server';
import { TopBar } from '@/components/shell/top-bar';
import { DemoStrip } from '@/components/shell/demo-strip';
import { AppFooter } from '@/components/shell/app-footer';
import { ArrivalReporter } from '@/components/shell/arrival-reporter';
import { SkipNav } from '@/components/layout/SkipNav';
import { Providers } from '@/components/providers';
import { Toaster } from '@/components/ui/sonner';
import { InstallPrompt } from '@/components/pwa/install-prompt';
import { OnboardingTour } from '@/components/onboarding/Tour';
import { UpdateBanner } from '@/components/pwa/update-banner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import type { Locale } from '@/i18n/config';
import { routing } from '@/i18n/routing';
import { SITE_URL, absoluteUrl } from '@/lib/site';
import { ACTION_HEX } from '@/lib/palette';
import { languageAlternates } from '@/lib/metadata';
import { buildStructuredData } from '@/lib/structured-data';

/**
 * Open Graph expects a `language_TERRITORY` tag. Every supported locale gets
 * its own — the old ternary declared only Polish and Russian and told the
 * crawlers that the German, Spanish, Italian, Portuguese, Turkish and
 * Ukrainian pages were American English.
 */
const OPEN_GRAPH_LOCALE: Record<Locale, string> = {
  en: 'en_US',
  pl: 'pl_PL',
  ru: 'ru_RU',
  de: 'de_DE',
  es: 'es_ES',
  it: 'it_IT',
  pt: 'pt_PT',
  tr: 'tr_TR',
  uk: 'uk_UA',
};

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin', 'latin-ext'],
});
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin', 'latin-ext'],
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  // The browser chrome cannot read a CSS token, so the teal is written out
  // in `lib/palette.ts` and asserted against `--action` by the palette test.
  themeColor: ACTION_HEX,
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  const titles: Record<Locale, string> = {
    pl: 'Asystent Nieruchomości AI',
    en: 'AI Real Estate Assistant',
    ru: 'AI Ассистент по Недвижимости',
    de: 'KI-Immobilienassistent',
    es: 'Asistente Inmobiliario IA',
    it: 'Assistente Immobiliare IA',
    pt: 'Assistente Imobiliário IA',
    tr: 'Yapay Zeka Emlak Asistanı',
    uk: 'AI Асистент з Нерухомості',
  };

  const descriptions: Record<Locale, string> = {
    pl: 'Nowoczesne wyszukiwanie nieruchomości i analityka rynkowa',
    en: 'Next-gen real estate search and analytics',
    ru: 'Современный поиск недвижимости и аналитика рынка',
    de: 'Modernes Immobiliensuche und Marktanalyse',
    es: 'Búsqueda inmobiliaria y análisis de mercado de nueva generación',
    it: 'Ricerca immobiliare e analisi di mercato di nuova generazione',
    pt: 'Pesquisa imobiliária e análise de mercado de última geração',
    tr: 'Yeni nesil emlak arama ve pazar analizi',
    uk: 'Сучасний пошук нерухомості та аналітика ринку',
  };

  return {
    metadataBase: SITE_URL,
    title: {
      default: titles[locale as Locale] || titles.en,
      template: `%s | ${titles[locale as Locale] || titles.en}`,
    },
    description: descriptions[locale as Locale] || descriptions.en,
    keywords: [
      'AI real estate',
      'property search',
      'conversational AI',
      'FastAPI',
      'Next.js',
      'ChromaDB',
      'RAG',
      'mortgage calculator',
      'property valuation',
      'open source',
      'self-hosted',
      'real estate analytics',
    ],
    authors: [{ name: 'AleksNeStu', url: 'https://github.com/AleksNeStu' }],
    creator: 'AleksNeStu',
    publisher: 'AleksNeStu',
    category: 'technology',
    alternates: {
      // NO canonical here on purpose. A layout is inherited by every route
      // below it and does not know which route it is rendering, so a canonical
      // declared here is the same URL for all of them. The layout used to
      // declare the home page's URL, which told search engines that all thirty
      // routes were duplicates of the home page. Pages now fall back to
      // self-canonical, which is correct; a route that needs an explicit one
      // uses pageMetadata() from '@/lib/metadata'.
      languages: languageAlternates(),
    },
    openGraph: {
      title: titles[locale as Locale] || titles.en,
      description: descriptions[locale as Locale] || descriptions.en,
      siteName: 'AI Real Estate Assistant',
      locale: OPEN_GRAPH_LOCALE[locale as Locale] || 'en_US',
      type: 'website',
      images: [
        {
          url: absoluteUrl('/og-image.png'),
          width: 1200,
          height: 630,
          alt: 'AI Real Estate Assistant — Conversational AI for property search',
          type: 'image/png',
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: titles[locale as Locale] || titles.en,
      description: descriptions[locale as Locale] || descriptions.en,
      images: [absoluteUrl('/og-image.png')],
      creator: '@AleksNeStu',
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
    manifest: '/manifest.json',
    icons: {
      icon: [
        { url: '/icon-192x192.svg', sizes: '192x192', type: 'image/svg+xml' },
        { url: '/icon-512x512.svg', sizes: '512x512', type: 'image/svg+xml' },
      ],
      apple: '/apple-touch-icon.png',
    },
    appleWebApp: {
      capable: true,
      statusBarStyle: 'default',
      title: 'AI Real Estate Assistant',
    },
    formatDetection: {
      telephone: false,
      date: true,
      address: true,
    },
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  // Enable static rendering
  setRequestLocale(locale);

  // Default to dark theme for the demo, but allow explicit light choice
  // via localStorage.theme = 'light'. Without the explicit 'light' branch,
  // React's className="dark" hydration overrides any earlier removal, and
  // the page is stuck in dark mode (e.g. screenshot tools can't capture
  // a light theme for a page that pre-renders <html class="dark">).
  const darkThemeScript = `
    (function() {
      try {
        const stored = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (stored === 'light') {
          document.documentElement.classList.remove('dark');
        } else if (stored === 'dark' || (!stored && prefersDark)) {
          document.documentElement.classList.add('dark');
        }
      } catch (e) {
        // Fallback: always use dark mode for demo
        document.documentElement.classList.add('dark');
      }
    })();
  `;

  // Providing all messages to the client
  const messages = await getMessages();

  // The JSON-LD document speaks the language of the reader too — the FAQ
  // answers and the description come from the message catalogue.
  const tSeo = await getTranslations('seo.structuredData');
  const structuredData = buildStructuredData(locale as Locale, {
    description: tSeo('description'),
    keywords: tSeo('keywords'),
    languages: [
      tSeo('languages.en'),
      tSeo('languages.pl'),
      tSeo('languages.ru'),
      tSeo('languages.de'),
      tSeo('languages.es'),
      tSeo('languages.it'),
      tSeo('languages.pt'),
      tSeo('languages.tr'),
      tSeo('languages.uk'),
    ],
    faq: Array.from({ length: 8 }, (_, index) => ({
      question: tSeo(`faq.q${index + 1}`),
      answer: tSeo(`faq.a${index + 1}`),
    })),
  });

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(structuredData),
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: darkThemeScript,
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased min-h-screen flex flex-col`}
      >
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <UpdateBanner />
            <SkipNav />
            <ArrivalReporter />
            <TopBar />
            <DemoStrip />
            <main id="main-content" className="flex-1">
              <ErrorBoundary>{children}</ErrorBoundary>
            </main>
            <AppFooter />
            <InstallPrompt />
            <OnboardingTour />
            <Toaster />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
