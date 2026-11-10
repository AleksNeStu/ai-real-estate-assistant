'use client';

import { useEffect, useState } from 'react';
import { Play } from 'lucide-react';
import { useTranslations } from 'next-intl';

/**
 * The six seconds of the demo, on the landing.
 *
 * The clip is a build-time asset: the landing plays a file, it never calls
 * the model, so nothing here spends the deployment's key and the free tier
 * is not touched by the page.
 *
 * The poster carries the frame and the one teal action. The clip itself is
 * not in the page until the visitor asks for it - the file is fetched on the
 * click, so the landing keeps its budget on /en, and a visitor who never
 * clicks never downloads a megabyte.
 *
 * Where motion is not wanted, the poster is the whole thing: the clip is
 * never fetched and never plays.
 */

const CLIP_SRC = '/clips/demo-6s.mp4';
const POSTER_SRC = '/clips/poster.png';

export function DemoClip({ locale }: { locale: string }) {
  const t = useTranslations('landing');
  const [playing, setPlaying] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(query.matches);
    apply();
    query.addEventListener('change', apply);
    return () => query.removeEventListener('change', apply);
  }, []);

  return (
    <figure className="m-0 flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-[10px] border border-border bg-muted/40">
        <div className="aspect-[8/5] w-full">
          {playing ? (
            <video
              className="h-full w-full object-cover"
              src={CLIP_SRC}
              poster={POSTER_SRC}
              autoPlay
              muted
              loop
              playsInline
              aria-label={t('demo.clipAlt')}
            />
          ) : (
            <img
              src={POSTER_SRC}
              alt={t('demo.posterAlt')}
              className="h-full w-full object-cover"
              width={1280}
              height={800}
            />
          )}
        </div>

        {/* One teal action: the play button of the section. It is the only
            way into the clip, and it is gone once the clip is running. */}
        {!playing && !reduced ? (
          <button
            type="button"
            onClick={() => setPlaying(true)}
            aria-label={t('demo.play')}
            className="absolute inset-0 flex items-center justify-center rounded-[10px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-action text-action-foreground shadow-[0_4px_16px_rgb(9_9_11/0.45)] transition-transform hover:scale-105">
              <Play className="ml-0.5 h-6 w-6" aria-hidden="true" />
            </span>
          </button>
        ) : null}
      </div>

      {/* The routes are data, so they are in mono. */}
      <figcaption className="font-mono text-[12px] text-muted-foreground">
        /{locale}/search · /{locale}/chat
      </figcaption>
    </figure>
  );
}
