import { Bookmark, Clapperboard, Sparkles, UserRound } from 'lucide-react';
import type { AppView, UserProfile } from '../types';

interface NavbarProps {
  user: UserProfile;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
}

const navigation: { id: AppView; label: string; icon: typeof Sparkles }[] = [
  { id: 'recommendations', label: 'System Rekomendacji', icon: Sparkles },
  { id: 'saved', label: 'Moja lista', icon: Bookmark },
  { id: 'profile', label: 'Profil', icon: UserRound },
];

export function Navbar({ user, activeView, onViewChange }: NavbarProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-ink-950/95 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-[1480px] items-center px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={() => onViewChange('recommendations')}
          className="mr-6 flex items-center gap-2.5"
          aria-label="Przejdź do rekomendacji"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 text-white">
            <Clapperboard className="h-4 w-4" />
          </span>
          <span className="text-sm font-semibold tracking-tight text-white">Scene</span>
        </button>

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
          <div className="hidden items-center gap-2 text-[11px] text-slate-500 lg:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            System gotowy
          </div>
          <div className="flex items-center gap-2 py-1 pl-1 pr-2 text-xs text-slate-400">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-800 text-[10px] font-semibold text-slate-200">
              {user.initials}
            </span>
            <span className="hidden md:inline">{user.name.split(' ')[0]}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
