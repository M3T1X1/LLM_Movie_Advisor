import { Bookmark, MessageCircleMore } from 'lucide-react';

export function EmptyState({ onDiscover }: { onDiscover: () => void }) {
  return (
    <div className="flex min-h-[380px] flex-col items-center justify-center rounded-xl border border-dashed border-white/10 p-8 text-center">
      <span className="mb-5 flex h-11 w-11 items-center justify-center rounded-md bg-white/[0.04] text-slate-500">
        <Bookmark className="h-6 w-6" />
      </span>
      <h2 className="text-lg font-semibold text-white">Nie masz jeszcze zapisanych tytułów</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
        Porozmawiaj z doradcą i zapisz filmy, do których chcesz wrócić później.
      </p>
      <button
        type="button"
        onClick={onDiscover}
        className="mt-6 flex h-9 items-center gap-2 rounded-md bg-violet-600 px-3 text-xs font-medium text-white transition hover:bg-violet-500"
      >
        <MessageCircleMore className="h-4 w-4" />
        Znajdź coś dla mnie
      </button>
    </div>
  );
}
