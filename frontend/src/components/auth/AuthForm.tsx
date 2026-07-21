import { Eye, EyeOff, LockKeyhole } from 'lucide-react';
import type { ReactNode } from 'react';

export const inputClassName =
  'h-11 w-full rounded-lg border border-white/[0.09] bg-white/[0.025] pl-10 pr-3 text-sm text-white outline-none transition placeholder:text-slate-700 hover:border-white/[0.14] focus:border-violet-500/70 focus:ring-2 focus:ring-violet-500/10';

export function AuthPage({ title, description, onBack, children }: { title: string; description?: string; onBack?: () => void; children: ReactNode }) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute left-1/2 top-1/3 h-[420px] w-[420px] -translate-x-1/2 rounded-full bg-violet-600/[0.08] blur-3xl" />
        <div className="absolute bottom-0 right-0 h-72 w-72 rounded-full bg-blue-600/[0.05] blur-3xl" />
      </div>
      <section className="relative w-full max-w-md overflow-hidden rounded-2xl border border-white/[0.1] bg-[#0d0f15]/95 shadow-card backdrop-blur-xl">
        <div className="relative border-b border-white/[0.07] px-6 py-7 sm:px-8">
          {onBack && (
            <button type="button" onClick={onBack} className="absolute left-5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-lg text-slate-600 transition hover:bg-white/[0.05] hover:text-white" aria-label="Wróć do logowania">←</button>
          )}
          <h1 className="text-center text-2xl font-semibold tracking-[-0.03em] text-white sm:text-3xl">{title}</h1>
          {description && <p className="mx-auto mt-2 max-w-xs text-center text-xs leading-5 text-slate-600">{description}</p>}
        </div>
        {children}
      </section>
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

export function PrimaryButton({ children }: { children: ReactNode }) {
  return <button type="submit" className="flex h-11 w-full items-center justify-center rounded-lg bg-violet-600 text-sm font-semibold text-white transition hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0f15]">{children}</button>;
}
