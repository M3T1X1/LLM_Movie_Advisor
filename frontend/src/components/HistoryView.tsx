import { Clock3, History, RotateCcw, Sparkles } from 'lucide-react';
import type { RecommendationHistoryItem } from '../types';

interface HistoryViewProps {
  history: RecommendationHistoryItem[];
  onRepeat: (query: string) => void;
}

function fullDate(date: string) {
  return new Intl.DateTimeFormat('pl-PL', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function HistoryView({ history, onRepeat }: HistoryViewProps) {
  return (
    <section className="overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15]">
      <div className="border-b border-white/[0.06] p-5 sm:p-6">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-white/[0.04] text-slate-400">
            <History className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-white">Ostatnie rozmowy</h2>
            <p className="text-xs text-slate-500">Wróć do poprzedniego kontekstu jednym kliknięciem.</p>
          </div>
        </div>
      </div>
      <div className="divide-y divide-white/[0.05]">
        {history.map((item, index) => (
          <div key={item.id} className="group flex items-center gap-4 p-5 transition hover:bg-white/[0.02] sm:px-6">
            <span className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white/[0.03] text-slate-600 sm:flex">
              {index === 0 ? <Sparkles className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-slate-200">„{item.query}”</p>
              <p className="mt-1 text-[11px] text-slate-600">
                {fullDate(item.createdAt)} · {item.resultCount} rekomendacji
              </p>
            </div>
            <button
              type="button"
              onClick={() => onRepeat(item.query)}
              className="flex h-8 shrink-0 items-center gap-2 rounded-md border border-white/[0.08] px-3 text-[10px] font-medium text-slate-500 transition hover:border-white/15 hover:text-white"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Zapytaj ponownie</span>
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
