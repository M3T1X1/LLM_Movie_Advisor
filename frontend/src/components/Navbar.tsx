import {
  Bookmark,
  Bot,
  Clapperboard,
  History,
  Menu,
  Sparkles,
} from 'lucide-react';
import type { AppView, UserProfile } from '../types';

interface NavbarProps {
  user: UserProfile;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  onOpenProfile: () => void;
}

const navigation: { id: AppView; label: string; icon: typeof Sparkles }[] = [
  { id: 'recommendations', label: 'Odkrywaj', icon: Sparkles },
  { id: 'saved', label: 'Moja lista', icon: Bookmark },
  { id: 'history', label: 'Historia', icon: History },
];

export function Navbar({ user, activeView, onViewChange, onOpenProfile }: NavbarProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-ink-950/80 backdrop-blur-2xl">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={() => onViewChange('recommendations')}
          className="group flex items-center gap-3"
          aria-label="Przejdź do rekomendacji"
        >
          <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 shadow-glow">
            <Clapperboard className="h-5 w-5 text-white" />
            <span className="absolute inset-0 bg-white/10 opacity-0 transition-opacity group-hover:opacity-100" />
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-bold tracking-tight text-white">Scene AI</span>
            <span className="block text-[10px] font-medium uppercase tracking-[0.2em] text-slate-500">
              Movie advisor
            </span>
          </span>
        </button>

        <nav className="flex items-center gap-1 rounded-xl border border-white/5 bg-white/[0.025] p-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onViewChange(item.id)}
                className={`flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium transition sm:px-3.5 ${
                  isActive
                    ? 'bg-white/10 text-white shadow-sm'
                    : 'text-slate-500 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden md:inline">{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded-full border border-emerald-400/10 bg-emerald-400/5 px-3 py-1.5 text-xs text-emerald-300 lg:flex">
            <Bot className="h-3.5 w-3.5" />
            <span>4 agentów online</span>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]" />
          </div>
          <button
            type="button"
            onClick={onOpenProfile}
            className="flex h-9 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-2 transition hover:border-white/20 hover:bg-white/10 xl:hidden"
            aria-label="Otwórz profil"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 text-[10px] font-bold text-white">
              {user.initials}
            </span>
            <Menu className="h-4 w-4 text-slate-400" />
          </button>
        </div>
      </div>
    </header>
  );
}
