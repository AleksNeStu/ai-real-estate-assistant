'use client';

import React, { useCallback, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';

import { StepSubject } from './step-subject';
import { StepComparables, MIN_COMPARABLES } from './step-comparables';
import { StepAdjustments } from './step-adjustments';
import { StepPreview } from './step-preview';
import { StepExport } from './step-export';
import type { CMAReportResponse } from './report';
import type { Property, CMAComparable } from '@/lib/types';

interface CMAWizardState {
  currentStep: number;
  /** The furthest step the reader has reached - the stepper may open it. */
  furthestStep: number;
  subjectPropertyId: string | null;
  subjectProperty: Property | null;
  comparables: CMAComparable[];
  report: CMAReportResponse | null;
  isLoading: boolean;
}

const STEP_KEYS = ['subject', 'comparables', 'adjustments', 'preview', 'export'] as const;

/**
 * The comparative market analysis, step by step.
 *
 * The design draws the wizard as a rule with five numbered steps on it -
 * the ones the reader has reached carry the ink, the ones ahead stay grey -
 * and a single pair of buttons under the step. The step owns its content
 * and nothing else; the wizard owns where the reader is.
 */
export function CMAWizard() {
  const t = useTranslations('cma');
  const tPage = useTranslations('pages.cma');

  const [state, setState] = useState<CMAWizardState>({
    currentStep: 1,
    furthestStep: 1,
    subjectPropertyId: null,
    subjectProperty: null,
    comparables: [],
    report: null,
    isLoading: false,
  });

  const updateState = useCallback((updates: Partial<CMAWizardState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const goToStep = useCallback((step: number) => {
    setState((prev) =>
      step >= 1 && step <= prev.furthestStep
        ? { ...prev, currentStep: step }
        : prev
    );
  }, []);

  const nextStep = useCallback(() => {
    setState((prev) => {
      const next = Math.min(prev.currentStep + 1, STEP_KEYS.length);
      return {
        ...prev,
        currentStep: next,
        furthestStep: Math.max(prev.furthestStep, next),
      };
    });
  }, []);

  const prevStep = useCallback(() => {
    setState((prev) => ({ ...prev, currentStep: Math.max(prev.currentStep - 1, 1) }));
  }, []);

  const resetWizard = useCallback(() => {
    setState({
      currentStep: 1,
      furthestStep: 1,
      subjectPropertyId: null,
      subjectProperty: null,
      comparables: [],
      report: null,
      isLoading: false,
    });
  }, []);

  /**
   * Whether the reader may leave the step they are on.
   *
   * The subject has to be picked and the comparables have to be enough of
   * them; the report has to exist before it can be exported. Everything
   * else is free.
   */
  const canProceed = (() => {
    switch (state.currentStep) {
      case 1:
        return Boolean(state.subjectProperty);
      case 2:
        return state.comparables.length >= MIN_COMPARABLES;
      case 4:
        return Boolean(state.report);
      default:
        return true;
    }
  })();

  const renderStep = () => {
    switch (state.currentStep) {
      case 1:
        return (
          <StepSubject
            subjectPropertyId={state.subjectPropertyId}
            subjectProperty={state.subjectProperty}
            onPropertySelect={(property) => {
              updateState({
                subjectPropertyId: property.id || null,
                subjectProperty: property,
              });
            }}
          />
        );
      case 2:
        return (
          <StepComparables
            subjectPropertyId={state.subjectPropertyId}
            selectedComparables={state.comparables}
            onComparablesChange={(comparables) => updateState({ comparables })}
          />
        );
      case 3:
        return (
          <StepAdjustments
            comparables={state.comparables}
            onComparablesChange={(comparables) => updateState({ comparables })}
          />
        );
      case 4:
        return (
          <StepPreview
            subjectProperty={state.subjectProperty}
            comparables={state.comparables}
            report={state.report}
            onReportGenerated={(report) => updateState({ report })}
          />
        );
      case 5:
        return <StepExport report={state.report} onReset={resetWizard} />;
      default:
        return null;
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={tPage('title')}
          description={tPage('description')}
          actions={
            <MonoAnnotation>{t('stepOf', { step: state.currentStep, total: STEP_KEYS.length })}</MonoAnnotation>
          }
        />
      </div>

      <div className="flex flex-1 flex-col gap-6 px-6 py-6">
        <ol className="grid grid-cols-5 border-t-2 border-border">
          {STEP_KEYS.map((key, index) => {
            const stepNumber = index + 1;
            const reached = stepNumber <= state.furthestStep;
            const current = stepNumber === state.currentStep;
            return (
              <li key={key}>
                <button
                  type="button"
                  onClick={() => goToStep(stepNumber)}
                  disabled={!reached}
                  aria-current={current ? 'step' : undefined}
                  className={[
                    'flex w-full flex-col items-start gap-0.5 border-t-2 pt-2.5 text-left',
                    reached
                      ? 'border-foreground text-foreground'
                      : 'border-border text-muted-foreground',
                    reached && !current ? 'hover:opacity-80' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  style={{ marginTop: '-2px' }}
                >
                  <span className="font-mono text-[11px] font-medium">
                    {String(stepNumber).padStart(2, '0')}
                  </span>
                  <span className="text-[13px] font-medium">{t(`steps.${key}.title`)}</span>
                </button>
              </li>
            );
          })}
        </ol>

        <div className="flex flex-1 flex-col gap-5">{renderStep()}</div>

        <div className="flex items-center justify-between border-t border-border pt-4">
          <Button
            variant="outline"
            onClick={prevStep}
            disabled={state.currentStep === 1}
            className={state.currentStep === 1 ? 'opacity-40' : undefined}
          >
            {t('back')}
          </Button>
          <Button
            variant="ink"
            onClick={nextStep}
            disabled={state.currentStep === STEP_KEYS.length || !canProceed}
            className={state.currentStep === STEP_KEYS.length ? 'opacity-40' : undefined}
          >
            {state.currentStep === 4 ? t('continueToExport') : t('next')}
          </Button>
        </div>
      </div>
    </div>
  );
}
