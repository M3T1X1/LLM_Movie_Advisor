import { Bookmark, MessageCircleMore } from 'lucide-react';

export function EmptyState({ onDiscover }: { onDiscover: () => void }) {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-3xl border border-dashed border-white/10 bg-white/[0.015] p-8 text-center">
      <span className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-300 ring-1 ring-violet-400/15">
        <Bookmark className="h-6 w-6" />
      </span>
      <h2 className="text-xl font-bold text-white">Twoja lista czeka na pierwszy tytuł</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
        Porozmawiaj z doradcą i zapisz filmy, do których chcesz wrócić później.
      </p>
      <button
        type="button"
        onClick={onDiscover}
        className="mt-6 flex h-11 items-center gap-2 rounded-xl bg-white px-4 text-xs font-bold text-ink-950 transition hover:bg-violet-100"
      >
        <MessageCircleMore className="h-4 w-4" />
        Znajdź coś dla mnie
      </button>
    </div>
  );
}
