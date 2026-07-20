import { Bookmark, Sparkles, UserRound } from 'lucide-react';
import type { AppUser, AppView } from '../types';

interface NavbarProps {
  user: AppUser;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
}

const navigation: { id: AppView; label: string; icon: typeof Sparkles }[] = [
  { id: 'recommendations', label: 'System Rekomendacji', icon: Sparkles },
  { id: 'saved', label: 'Moja lista', icon: Bookmark },
  { id: 'profile', label: 'Profil', icon: UserRound },
];

export function Navbar({ user, activeView, onViewChange }: NavbarProps) {
  const initials = user.username.slice(0, 2).toUpperCase();

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-ink-950/95 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-[1480px] items-center px-4 sm:px-6 lg:px-8">
        <nav className="flex h-full items-center gap-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onViewChange(item.id)}
                className={`relative flex h-full items-center gap-2 px-3 text-xs font-medium transition-colors ${
                  isActive ? 'text-white' : 'text-slate-500 hover:text-slate-200'
                }`}
              >
                <Icon className="h-3.5 w-3.5 sm:hidden" />
                <span className="hidden sm:inline">{item.label}</span>
                {isActive && <span className="absolute inset-x-3 bottom-0 h-px bg-violet-400" />}
              </button>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-4">
          <div className="flex items-center gap-2 py-1 pl-1 pr-2 text-xs text-slate-400">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-800 text-[10px] font-semibold text-slate-200">
              {initials}
            </span>
            <span className="hidden md:inline">{user.username}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
