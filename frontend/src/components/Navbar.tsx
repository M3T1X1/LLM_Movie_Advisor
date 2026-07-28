import { BarChart3, Bookmark, CalendarDays, Flame, Library, LogOut, Sparkles, UserRound } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { AppUser, AppView } from '../types';

interface NavbarProps {
  user: AppUser;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  onLogout: () => void;
}

const primaryNavigation: { id: AppView; label: string; shortLabel: string; icon: typeof Sparkles }[] = [
  { id: 'recommendations', label: 'System Rekomendacji', shortLabel: 'Doradca', icon: Sparkles },
  { id: 'catalog', label: 'Baza filmów i seriali', shortLabel: 'Katalog', icon: Library },
  { id: 'trends', label: 'Trendy', shortLabel: 'Trendy', icon: Flame },
  { id: 'upcoming', label: 'Przyszłe premiery', shortLabel: 'Premiery', icon: CalendarDays },
];

export function Navbar({ user, activeView, onViewChange, onLogout }: NavbarProps) {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const initials = user.username.slice(0, 2).toUpperCase();

  useEffect(() => {
    if (!isUserMenuOpen) return;

    const handleOutsideClick = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setIsUserMenuOpen(false);
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsUserMenuOpen(false);
    };

    document.addEventListener('mousedown', handleOutsideClick);
    window.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isUserMenuOpen]);

  const selectView = (view: AppView) => {
    setIsUserMenuOpen(false);
    onViewChange(view);
  };

  const logout = () => {
    setIsUserMenuOpen(false);
    onLogout();
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.09] bg-ink-950/95 backdrop-blur-lg">
      <div className="mx-auto flex h-16 max-w-[1480px] items-center px-3 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={() => onViewChange('recommendations')}
          className="mr-8 hidden shrink-0 text-left lg:block"
          aria-label="Filmiq — przejdź do doradcy"
        >
          <span>
            <span className="font-display block text-lg leading-none text-slate-100">Filmiq</span>
            <span className="mt-1 block text-[8px] uppercase tracking-[0.18em] text-slate-600">Doradca Filmowy</span>
          </span>
        </button>
        <nav className="flex h-full min-w-0 items-center">
          {primaryNavigation.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onViewChange(item.id)}
                aria-label={item.label}
                aria-current={isActive ? 'page' : undefined}
                className={`relative flex h-full min-w-11 items-center justify-center gap-2 px-2 text-xs font-medium transition-colors sm:px-3 ${
                  isActive ? 'text-slate-100' : 'text-slate-600 hover:text-slate-200'
                }`}
              >
                <Icon className="h-4 w-4 md:hidden" />
                <span className="hidden md:inline">{item.shortLabel}</span>
                {isActive && <span className="absolute inset-x-2 bottom-0 h-0.5 bg-violet-400 sm:inset-x-3" />}
              </button>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <span className="hidden h-5 w-px bg-white/[0.08] sm:block" />

          <div ref={menuRef} className="relative">
            <button
              type="button"
              onClick={() => setIsUserMenuOpen((current) => !current)}
              aria-label={`Menu użytkownika: ${user.username}`}
              aria-haspopup="menu"
              aria-expanded={isUserMenuOpen}
              className={`relative flex h-9 w-9 items-center justify-center rounded-full border text-[10px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60 ${
                isUserMenuOpen || activeView === 'profile'
                  ? 'border-violet-400/35 bg-violet-500/15 text-violet-100'
                  : 'border-white/[0.1] bg-white/[0.04] text-slate-300 hover:border-white/20 hover:bg-white/[0.07] hover:text-white'
              }`}
            >
              {initials}
              <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-ink-950 bg-emerald-400" aria-hidden="true" />
            </button>

            {isUserMenuOpen && (
              <div
                role="menu"
                aria-label="Menu konta"
                className="absolute right-0 top-[calc(100%+0.65rem)] w-64 overflow-hidden rounded-lg border border-white/[0.12] bg-ink-900 shadow-2xl"
              >
                <div className="border-b border-white/[0.07] px-4 py-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-xs font-semibold text-violet-100">
                      {initials}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-white">{user.username}</p>
                      <p className="mt-1 truncate text-[10px] text-slate-600">{user.email}</p>
                    </div>
                  </div>
                </div>
                <div className="p-1.5">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => selectView('profile')}
                    className="flex h-9 w-full items-center gap-3 rounded-lg px-3 text-left text-xs text-slate-400 transition hover:bg-white/[0.05] hover:text-white"
                  >
                    <UserRound className="h-3.5 w-3.5" />
                    Przejdź do profilu
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => selectView('saved')}
                    className="flex h-9 w-full items-center gap-3 rounded-lg px-3 text-left text-xs text-slate-400 transition hover:bg-white/[0.05] hover:text-white"
                  >
                    <Bookmark className="h-3.5 w-3.5" />
                    Moja lista
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => selectView('analytics')}
                    className="flex h-9 w-full items-center gap-3 rounded-lg px-3 text-left text-xs text-slate-400 transition hover:bg-white/[0.05] hover:text-white"
                  >
                    <BarChart3 className="h-3.5 w-3.5" />
                    Analiza oglądania
                  </button>
                  <div className="my-1 border-t border-white/[0.06]" />
                  <button
                    type="button"
                    role="menuitem"
                    onClick={logout}
                    className="flex h-9 w-full items-center gap-3 rounded-lg px-3 text-left text-xs text-slate-500 transition hover:bg-red-500/[0.08] hover:text-red-300"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    Wyloguj się
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
