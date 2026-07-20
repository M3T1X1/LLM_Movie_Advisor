import {
  BrainCircuit,
  Check,
  Database,
  ListFilter,
  MessageSquareText,
  type LucideIcon,
} from 'lucide-react';
import type { AgentKey, AgentStep } from '../types';

const agentIcons: Record<AgentKey, LucideIcon> = {
  profiling: BrainCircuit,
  retrieval: Database,
  ranking: ListFilter,
  explanation: MessageSquareText,
};

export function AgentStatus({ steps }: { steps: AgentStep[] }) {
  return (
    <div className="mx-4 mb-3 overflow-hidden rounded-2xl border border-violet-400/15 bg-violet-500/[0.06] sm:mx-5">
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-400" />
          </span>
          <span className="text-xs font-semibold text-violet-200">Przepływ agentowy</span>
        </div>
        <span className="text-[10px] font-medium uppercase tracking-widest text-slate-500">LangGraph</span>
      </div>
      <div className="grid grid-cols-2 gap-px bg-white/5 sm:grid-cols-4">
        {steps.map((step) => {
          const Icon = agentIcons[step.key];
          const isWorking = step.status === 'working';
          const isCompleted = step.status === 'completed';

          return (
            <div key={step.key} className="bg-ink-900/80 px-3 py-3">
              <div className="mb-2 flex items-center justify-between">
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-lg ${
                    isWorking
                      ? 'bg-violet-500/20 text-violet-300'
                      : isCompleted
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : 'bg-white/5 text-slate-600'
                  }`}
                >
                  {isCompleted ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <Icon className={`h-3.5 w-3.5 ${isWorking ? 'animate-pulse' : ''}`} />
                  )}
                </span>
                {isWorking && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />}
              </div>
              <p className={`text-[11px] font-medium ${isWorking ? 'text-white' : 'text-slate-400'}`}>
                {step.name.replace('Agent ', '')}
              </p>
              <p className="mt-0.5 line-clamp-1 text-[9px] text-slate-600">
                {isCompleted ? 'Gotowe' : step.activity}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
