import {
  Bookmark,
  BrainCircuit,
  ChevronRight,
  Clock3,
  Eye,
  Heart,
  History,
  Settings,
  Sparkles,
  X,
} from 'lucide-react';
import type { RecommendationHistoryItem, UserProfile } from '../types';

interface UserProfileSidebarProps {
  user: UserProfile;
  history: RecommendationHistoryItem[];
  savedCount: number;
  watchedCount: number;
  isOpen: boolean;
  onClose: () => void;
}

function relativeDate(date: string) {
  const days = Math.max(1, Math.round((Date.now() - new Date(date).getTime()) / 86_400_000));
  return days === 1 ? 'wczoraj' : `${days} dni temu`;
}

function ProfileContent({
  user,
  history,
  savedCount,
  watchedCount,
}: Omit<UserProfileSidebarProps, 'isOpen' | 'onClose'>) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-white/[0.06] p-5">
        <div className="mb-5 flex items-center gap-3">
          <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 text-sm font-bold text-white shadow-glow">
            {user.initials}
            <span className="absolute -bottom-1 -right-1 h-3.5 w-3.5 rounded-full border-2 border-ink-900 bg-emerald-400" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-semibold text-white">{user.name}</h2>
            <p className="truncate text-xs text-slate-600">{user.email}</p>
          </div>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-600 transition hover:bg-white/5 hover:text-slate-300"
            aria-label="Ustawienia profilu"
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-3">
            <div className="mb-2 flex items-center gap-1.5 text-slate-600">
              <Bookmark className="h-3 w-3" />
              <span className="text-[9px] uppercase tracking-wider">Zapisane</span>
            </div>
            <p className="text-lg font-bold text-white">{savedCount}</p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-3">
            <div className="mb-2 flex items-center gap-1.5 text-slate-600">
              <Eye className="h-3 w-3" />
              <span className="text-[9px] uppercase tracking-wider">Obejrzane</span>
            </div>
            <p className="text-lg font-bold text-white">{watchedCount}</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 [scrollbar-color:rgba(148,163,184,0.15)_transparent]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BrainCircuit className="h-3.5 w-3.5 text-violet-400" />
              <h3 className="text-xs font-semibold text-slate-300">Twój profil gustu</h3>
            </div>
            <span className="text-[10px] font-medium text-emerald-400">82% pewności</span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-white/5">
            <div className="h-full w-[82%] rounded-full bg-gradient-to-r from-violet-500 to-blue-500" />
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-slate-600">
              <Heart className="h-3 w-3" />
              Ulubione gatunki
            </div>
            <div className="flex flex-wrap gap-1.5">
              {user.favoriteGenres.map((genre) => (
                <span
                  key={genre}
                  className="rounded-lg border border-violet-400/10 bg-violet-500/[0.08] px-2.5 py-1.5 text-[10px] font-medium text-violet-200"
                >
                  {genre}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-slate-600">
              <Sparkles className="h-3 w-3" />
              Odczytane preferencje
            </div>
            <ul className="space-y-2">
              {user.preferences.slice(0, 4).map((preference) => (
                <li key={preference} className="flex items-start gap-2 text-[11px] leading-relaxed text-slate-400">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-blue-400" />
                  {preference}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <div className="my-6 h-px bg-white/[0.06]" />

        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-3.5 w-3.5 text-blue-400" />
              <h3 className="text-xs font-semibold text-slate-300">Ostatnie rozmowy</h3>
            </div>
            <button type="button" className="text-[10px] text-slate-600 transition hover:text-slate-300">
              Wszystkie
            </button>
          </div>
          <div className="space-y-2">
            {history.slice(0, 3).map((item) => (
              <button
                key={item.id}
                type="button"
                className="group flex w-full items-center gap-3 rounded-xl border border-transparent p-2.5 text-left transition hover:border-white/[0.06] hover:bg-white/[0.025]"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/[0.04] text-slate-600 group-hover:text-blue-300">
                  <Clock3 className="h-3.5 w-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[11px] text-slate-400 group-hover:text-slate-200">
                    {item.query}
                  </span>
                  <span className="mt-0.5 block text-[9px] text-slate-700">
                    {relativeDate(item.createdAt)} · {item.resultCount} propozycji
                  </span>
                </span>
                <ChevronRight className="h-3 w-3 text-slate-700" />
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="border-t border-white/[0.06] p-4">
        <div className="rounded-xl border border-blue-400/10 bg-blue-500/[0.05] p-3">
          <p className="text-[10px] leading-relaxed text-slate-500">
            Profil uczy się wyłącznie na podstawie Twoich rozmów i ocen. Możesz go wyczyścić w
            ustawieniach.
          </p>
        </div>
      </div>
    </div>
  );
}

export function UserProfileSidebar(props: UserProfileSidebarProps) {
  const contentProps = {
    user: props.user,
    history: props.history,
    savedCount: props.savedCount,
    watchedCount: props.watchedCount,
  };

  return (
    <>
      <aside className="sticky top-24 hidden h-[calc(100vh-7.5rem)] w-72 shrink-0 overflow-hidden rounded-3xl border border-white/[0.07] bg-ink-900/70 xl:block">
        <ProfileContent {...contentProps} />
      </aside>

      {props.isOpen && (
        <div className="fixed inset-0 z-50 xl:hidden">
          <button
            type="button"
            onClick={props.onClose}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            aria-label="Zamknij profil"
          />
          <aside className="absolute inset-y-0 right-0 w-[min(88vw,340px)] border-l border-white/10 bg-ink-900 shadow-2xl">
            <button
              type="button"
              onClick={props.onClose}
              className="absolute right-4 top-4 z-10 flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 text-slate-400"
              aria-label="Zamknij profil"
            >
              <X className="h-4 w-4" />
            </button>
            <ProfileContent {...contentProps} />
          </aside>
        </div>
      )}
    </>
  );
}
