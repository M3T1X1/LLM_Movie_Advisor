import { Bookmark, Clock3, Eye, Settings, X } from 'lucide-react';
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
      <div className="border-b border-white/[0.07] p-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-slate-800 text-xs font-semibold text-slate-200">
            {user.initials}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-xs font-semibold text-white">{user.name}</h2>
            <p className="mt-0.5 truncate text-[10px] text-slate-600">{user.email}</p>
          </div>
          <button
            type="button"
            className="text-slate-600 transition hover:text-slate-300"
            aria-label="Ustawienia profilu"
          >
            <Settings className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="mt-4 flex gap-5 border-t border-white/[0.05] pt-3">
          <div>
            <p className="text-sm font-semibold text-white">{savedCount}</p>
            <p className="mt-0.5 flex items-center gap-1 text-[9px] text-slate-600">
              <Bookmark className="h-2.5 w-2.5" /> zapisane
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">{watchedCount}</p>
            <p className="mt-0.5 flex items-center gap-1 text-[9px] text-slate-600">
              <Eye className="h-2.5 w-2.5" /> obejrzane
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 [scrollbar-color:rgba(148,163,184,0.12)_transparent]">
        <section>
          <h3 className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-600">Profil gustu</h3>

          <div className="mt-4">
            <p className="mb-2 text-[10px] text-slate-500">Najczęściej wybierasz</p>
            <div className="flex flex-wrap gap-1.5">
              {user.favoriteGenres.map((genre) => (
                <span key={genre} className="rounded border border-white/[0.08] px-2 py-1 text-[10px] text-slate-400">
                  {genre}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <p className="mb-2 text-[10px] text-slate-500">Zapamiętane preferencje</p>
            <ul className="space-y-2.5">
              {user.preferences.slice(0, 4).map((preference) => (
                <li key={preference} className="flex items-start gap-2 text-[10px] leading-4 text-slate-500">
                  <span className="mt-1.5 h-1 w-1 shrink-0 bg-violet-400" />
                  {preference}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <div className="my-6 h-px bg-white/[0.06]" />

        <section>
          <h3 className="text-[10px] font-medium uppercase tracking-[0.12em] text-slate-600">Ostatnie rozmowy</h3>
          <div className="mt-3 space-y-1">
            {history.slice(0, 3).map((item) => (
              <button
                key={item.id}
                type="button"
                className="group flex w-full gap-2.5 py-2 text-left"
              >
                <Clock3 className="mt-0.5 h-3 w-3 shrink-0 text-slate-700 group-hover:text-slate-500" />
                <span className="min-w-0">
                  <span className="block truncate text-[10px] text-slate-500 group-hover:text-slate-300">
                    {item.query}
                  </span>
                  <span className="mt-0.5 block text-[9px] text-slate-700">
                    {relativeDate(item.createdAt)} · {item.resultCount} propozycji
                  </span>
                </span>
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="border-t border-white/[0.06] p-4">
        <p className="text-[9px] leading-4 text-slate-700">
          Profil powstaje na podstawie rozmów i Twojej aktywności.
        </p>
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
      <aside className="sticky top-[76px] hidden h-[calc(100vh-6rem)] w-60 shrink-0 overflow-hidden border-r border-white/[0.07] xl:block">
        <ProfileContent {...contentProps} />
      </aside>

      {props.isOpen && (
        <div className="fixed inset-0 z-50 xl:hidden">
          <button
            type="button"
            onClick={props.onClose}
            className="absolute inset-0 bg-black/70"
            aria-label="Zamknij profil"
          />
          <aside className="absolute inset-y-0 right-0 w-[min(88vw,320px)] border-l border-white/10 bg-ink-900 shadow-2xl">
            <button
              type="button"
              onClick={props.onClose}
              className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-md bg-white/5 text-slate-400"
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
