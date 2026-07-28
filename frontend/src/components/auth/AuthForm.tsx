import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import type { ReactNode } from 'react';

export const inputClassName =
  'h-11 w-full rounded-md border border-white/[0.12] bg-ink-950 pl-10 pr-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 hover:border-white/20 focus:border-violet-400 focus:ring-2 focus:ring-violet-500/10';

export function AuthPage({ title, description, onBack, children }: { title: string; description?: string; onBack?: () => void; children: ReactNode }) {
  return (
    <main className="grid min-h-screen bg-ink-950 lg:grid-cols-[minmax(360px,0.82fr)_minmax(480px,1.18fr)]">
      <div className="relative hidden overflow-hidden border-r border-white/[0.09] bg-ink-900 p-10 lg:flex lg:flex-col xl:p-14" aria-hidden="true">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 bg-violet-500" />
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-300">Filmiq</span>
        </div>
        <blockquote className="my-auto max-w-lg self-center text-center">
          <p className="font-display text-4xl leading-[1.12] text-slate-100 xl:text-5xl">
            Dobry seans zaczyna się od właściwego pytania.
          </p>
          <footer className="mx-auto mt-6 max-w-md text-xs leading-5 text-slate-500">
            Rekomendacje oparte na nastroju, kontekście i Twojej historii — bez bezmyślnego przewijania.
          </footer>
        </blockquote>
      </div>
      <div className="flex items-center justify-center px-4 py-10 sm:px-8">
      <section className="w-full max-w-md">
        <div className="relative border-b border-white/[0.1] px-1 pb-7">
          <div className="mb-10 flex items-center gap-2.5 lg:hidden">
            <span className="h-2 w-2 bg-violet-500" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-300">Filmiq</span>
          </div>
          {onBack && (
            <button type="button" onClick={onBack} className="absolute right-0 top-0 flex h-8 items-center px-2 text-xs text-slate-500 transition hover:text-white" aria-label="Wróć do logowania">← Wróć</button>
          )}
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-400">Twoje kino, lepiej wybrane</p>
          <h1 className="text-4xl tracking-[-0.035em] text-slate-100 sm:text-5xl">{title}</h1>
          {description && <p className="mt-3 max-w-xs text-sm leading-6 text-slate-500">{description}</p>}
        </div>
        {children}
      </section>
      </div>
    </main>
  );
}

export function AuthField({ label, icon, children }: { label: string; icon: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.1em] text-slate-500">{label}</span>
      <span className="relative block">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600">{icon}</span>
        {children}
      </span>
    </label>
  );
}

export function PasswordField({ label, value, visible, error, autoComplete, onChange, onToggle }: { label: string; value: string; visible: boolean; error: string | null; autoComplete: string; onChange: (value: string) => void; onToggle?: () => void }) {
  return (
    <AuthField label={label} icon={<LockKeyhole className="h-4 w-4" />}>
      <input type={visible ? 'text' : 'password'} value={value} onChange={(event) => onChange(event.target.value)} autoComplete={autoComplete} placeholder="Wprowadź hasło" aria-invalid={Boolean(error)} className={`${inputClassName} ${onToggle ? 'pr-11' : ''}`} />
      {onToggle && (
        <button type="button" onClick={onToggle} className="absolute right-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-slate-600 transition hover:bg-white/[0.05] hover:text-slate-300" aria-label={visible ? 'Ukryj hasło' : 'Pokaż hasło'}>
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      )}
    </AuthField>
  );
}

export function PrimaryButton({ children, disabled = false }: { children: ReactNode; disabled?: boolean }) {
  return <button type="submit" disabled={disabled} className="flex h-11 w-full items-center justify-center rounded-md bg-violet-600 text-sm font-semibold text-white transition hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950 disabled:cursor-not-allowed disabled:opacity-60">{children}</button>;
}
