import type { Metadata, Viewport } from 'next';
import { Geist, Geist_Mono, Cinzel } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, setRequestLocale } from 'next-intl/server';
import { MainNav } from '@/components/layout/main-nav';
import { SkipNav } from '@/components/layout/SkipNav';
import { DemoBanner } from '@/components/layout/demo-banner';
import { Providers } from '@/components/providers';
import { Toaster } from '@/components/ui/sonner';
import { InstallPrompt } from '@/components/pwa/install-prompt';
import { UpdateBanner } from '@/components/pwa/update-banner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import type { Locale } from '@/i18n/config';
import { routing } from '@/i18n/routing';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

// Using Cinzel as a stand-in for "Phantom Templar" style
const fontTemplar = Cinzel({
  variable: '--font-templar',
  subsets: ['latin'],
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
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
    title: {
      default: titles[locale as Locale] || titles.en,
      template: `%s | ${titles[locale as Locale] || titles.en}`,
    },
    description: descriptions[locale as Locale] || descriptions.en,
    alternates: {
      canonical: `/${locale}`,
      languages: {
        pl: '/pl',
        en: '/en',
        ru: '/ru',
      },
    },
    openGraph: {
      title: titles[locale as Locale] || titles.en,
      description: descriptions[locale as Locale] || descriptions.en,
      siteName: 'AI Real Estate Assistant',
      locale: locale === 'pl' ? 'pl_PL' : locale === 'ru' ? 'ru_RU' : 'en_US',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: titles[locale as Locale] || titles.en,
      description: descriptions[locale as Locale] || descriptions.en,
    },
    robots: {
      index: true,
      follow: true,
    },
    manifest: '/manifest.json',
    themeColor: '#2563eb',
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

  // Force dark theme as default for demo - persists across language changes
  const darkThemeScript = `
    (function() {
      try {
        const stored = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (stored === 'dark' || (!stored && prefersDark)) {
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

  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'WebApplication',
              name: 'AI Real Estate Assistant',
              description: 'Next-gen real estate search and analytics',
              applicationCategory: 'BusinessApplication',
              operatingSystem: 'Web',
              offers: {
                '@type': 'Offer',
                price: '0',
                priceCurrency: 'EUR',
              },
            }),
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: darkThemeScript,
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${fontTemplar.variable} antialiased min-h-screen flex flex-col`}
      >
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <DemoBanner />
            <UpdateBanner />
            <SkipNav />
            <header className="border-b bg-background">
              <div className="flex h-16 items-center px-4 container mx-auto">
                <MainNav />
              </div>
            </header>
            <main id="main-content" className="flex-1">
              <ErrorBoundary>{children}</ErrorBoundary>
            </main>
            <InstallPrompt />
            <Toaster />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
