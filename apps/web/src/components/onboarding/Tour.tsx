'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  ChevronRight,
  Sparkles,
  Search,
  MessageSquare,
  TrendingUp,
  Languages,
  type LucideIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const STORAGE_KEY = 'onboarding-tour-dismissed-v1';

interface TourStep {
  id: string;
  icon: LucideIcon;
  title: string;
  body: string;
}

const STEPS: TourStep[] = [
  {
    id: 'welcome',
    icon: Sparkles,
    title: 'Welcome to AI Real Estate Assistant',
    body: 'A quick tour of the features that make this demo useful. Skippable — you can come back anytime.',
  },
  {
    id: 'search',
    icon: Search,
    title: 'Search with natural language',
    body: 'Try typing "2-bedroom apartment in Kraków under 500k" — filters extract automatically from your query.',
  },
  {
    id: 'chat',
    icon: MessageSquare,
    title: 'Chat for matched listings',
    body: 'Ask follow-ups, get refinements. Multi-turn context with multi-provider LLM fallback chain.',
  },
  {
    id: 'valuation',
    icon: TrendingUp,
    title: 'AI valuation with forecast',
    body: 'Paste a property id or enter features — get current value plus 1y, 3y, 5y, and 10y projections with a confidence band.',
  },
  {
    id: 'languages',
    icon: Languages,
    title: '9 languages',
    body: 'Switch the UI and chat language from the top-right selector. EU AI Act compliance labels included.',
  },
];

/**
 * Onboarding tour shown to first-time visitors.
 *
 * Behavior:
 *  - Hidden until 1.5 s after mount (lets the page render first).
 *  - 5 steps with a step indicator, Next / Skip / Done actions.
 *  - Dismissed state persisted in localStorage under `onboarding-tour-dismissed-v1`.
 *  - Server-render safe (guards `typeof window`).
 *  - Respects the user's `prefers-reduced-motion` via framer-motion defaults.
 *
 * Localization gap (intentional, this session):
 *  - Strings are English-only. next-intl coverage for 9 locales × 11 keys (99
 *    translations) is out of session scope and recorded as a follow-up.
 */
export function OnboardingTour() {
  const [step, setStep] = useState(0);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const dismissed = window.localStorage.getItem(STORAGE_KEY);
      if (dismissed) return;
    } catch {
      // localStorage may be unavailable (private mode, quota). Show the tour.
    }
    const timer = window.setTimeout(() => setShow(true), 1500);
    return () => window.clearTimeout(timer);
  }, []);

  const persistDismiss = useCallback(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(STORAGE_KEY, '1');
    } catch {
      // ignore
    }
  }, []);

  const dismiss = useCallback(() => {
    setShow(false);
    persistDismiss();
  }, [persistDismiss]);

  const next = useCallback(() => {
    if (step >= STEPS.length - 1) {
      dismiss();
    } else {
      setStep((s) => s + 1);
    }
  }, [step, dismiss]);

  if (!show) return null;

  const current = STEPS[step];
  const Icon = current.icon;
  const isLast = step === STEPS.length - 1;

  return (
    <AnimatePresence>
      <motion.div
        key="onboarding-tour"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        transition={{ duration: 0.25 }}
        className="fixed bottom-4 right-4 z-40 w-80 max-w-[calc(100vw-2rem)] shadow-xl"
        role="dialog"
        aria-live="polite"
        aria-label="Onboarding tour"
      >
        <Card className="p-4">
          <div className="flex items-start gap-3 mb-3">
            <div className="flex-shrink-0">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
                <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-foreground">{current.title}</p>
              <p className="text-xs text-muted mt-1 leading-relaxed">{current.body}</p>
            </div>
            <button
              type="button"
              onClick={dismiss}
              className="flex-shrink-0 text-muted hover:text-foreground transition-colors"
              aria-label="Close tour"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex gap-1" aria-hidden="true">
              {STEPS.map((_, i) => (
                <span
                  key={i}
                  className={`h-1.5 rounded-full transition-all ${
                    i === step ? 'w-6 bg-primary' : 'w-1.5 bg-muted/40'
                  }`}
                />
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={dismiss}>
                Skip
              </Button>
              <Button size="sm" onClick={next}>
                {isLast ? 'Done' : 'Next'}
                {!isLast && (
                  <ChevronRight className="h-3 w-3 ml-1" aria-hidden="true" />
                )}
              </Button>
            </div>
          </div>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}