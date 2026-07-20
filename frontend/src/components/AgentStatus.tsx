import { Check, LoaderCircle } from 'lucide-react';
import type { AgentStep } from '../types';

export function AgentStatus({ steps }: { steps: AgentStep[] }) {
  return (
    <div className="mx-4 mb-3 border-t border-white/[0.06] pt-3 sm:mx-5">
      <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-600">
        Przetwarzanie
      </p>
      <div className="space-y-1.5">
        {steps.map((step) => {
          const isWorking = step.status === 'working';
          const isCompleted = step.status === 'completed';

          return (
            <div key={step.key} className="flex items-center gap-2.5 text-[11px]">
              <span
                className={`flex h-4 w-4 items-center justify-center ${
                  isWorking ? 'text-violet-300' : isCompleted ? 'text-emerald-400' : 'text-slate-700'
                }`}
              >
                {isWorking ? (
                  <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                ) : isCompleted ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  <span className="h-1 w-1 rounded-full bg-current" />
                )}
              </span>
              <span className={isWorking ? 'text-slate-200' : 'text-slate-500'}>{step.name}</span>
              <span className="ml-auto hidden truncate text-slate-700 sm:block">
                {isCompleted ? 'Gotowe' : step.activity}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
