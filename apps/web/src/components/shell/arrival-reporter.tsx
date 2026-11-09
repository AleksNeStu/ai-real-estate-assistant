'use client';

import { useEffect } from 'react';

import { reportArrival } from '@/lib/attribution';

/**
 * The arrival reporter.
 *
 * A same-site link carries `?from=<slot>`; on arrival the slot is reported
 * as a navigation interaction and the parameter is dropped, so a reload does
 * not count the same arrival twice.
 *
 * It sits in the root layout because the arrival can happen on any route -
 * the landing links into the app with a slot, and the app links back out
 * with one.
 */
export function ArrivalReporter() {
  useEffect(() => {
    void reportArrival();
  }, []);

  return null;
}
