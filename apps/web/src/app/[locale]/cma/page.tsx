'use client';

import { CMAWizard } from '@/components/cma/cma-wizard';

/**
 * The comparative market analysis.
 *
 * The route is thin on purpose: the wizard carries the header, the stepper
 * and the five steps, and the page only says where the wizard goes.
 */
export default function CMAPage() {
  return <CMAWizard />;
}
