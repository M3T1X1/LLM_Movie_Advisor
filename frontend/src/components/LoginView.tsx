import { Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { useState, type FormEvent } from 'react';

export function LoginView({ onLogin }: { onLogin: (email: string, password: string) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLocaleLowerCase('pl-PL');

    if (!normalizedEmail || !password) {
      setError('Podaj adres e-mail i hasło.');
      return;
    }

    setError(null);
    onLogin(normalizedEmail, password);
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute left-1/2 top-1/3 h-[420px] w-[420px] -translate-x-1/2 rounded-full bg-violet-600/[0.08] blur-3xl" />
        <div className="absolute bottom-0 right-0 h-72 w-72 rounded-full bg-blue-600/[0.05] blur-3xl" />
      </div>

      <section className="relative w-full max-w-md overflow-hidden rounded-2xl border border-white/[0.1] bg-[#0d0f15]/95 shadow-card backdrop-blur-xl">
        <div className="border-b border-white/[0.07] px-6 py-7 sm:px-8">
          <h1 className="text-2xl text-center font-semibold tracking-[-0.03em] text-white sm:text-3xl">
            Zaloguj się
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 px-6 py-7 sm:px-8" noValidate>
          <LoginField label="Adres e-mail" icon={<Mail className="h-4 w-4" />}>
            <input
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setError(null);
              }}
              autoComplete="email"
              autoFocus
              placeholder="Wprowadź email"
              aria-invalid={Boolean(error)}
              className="h-11 w-full rounded-lg border border-white/[0.09] bg-white/[0.025] pl-10 pr-3 text-sm text-white outline-none transition placeholder:text-slate-700 hover:border-white/[0.14] focus:border-violet-500/70 focus:ring-2 focus:ring-violet-500/10"
            />
          </LoginField>

          <LoginField label="Hasło" icon={<LockKeyhole className="h-4 w-4" />}>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
                setError(null);
              }}
              autoComplete="current-password"
              placeholder="Wprowadź hasło"
              aria-invalid={Boolean(error)}
              className="h-11 w-full rounded-lg border border-white/[0.09] bg-white/[0.025] pl-10 pr-11 text-sm text-white outline-none transition placeholder:text-slate-700 hover:border-white/[0.14] focus:border-violet-500/70 focus:ring-2 focus:ring-violet-500/10"
            />
            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
              className="absolute right-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-slate-600 transition hover:bg-white/[0.05] hover:text-slate-300"
              aria-label={showPassword ? 'Ukryj hasło' : 'Pokaż hasło'}
            >
              {showPassword ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            </button>
          </LoginField>

          <div className="min-h-5" aria-live="polite">
            {error && <p className="text-xs text-red-300">{error}</p>}
          </div>

          <button
            type="submit"
            className="flex h-11 w-full items-center justify-center rounded-lg bg-violet-600 text-sm font-semibold text-white transition hover:bg-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d0f15]"
          >
            Zaloguj się
          </button>
        </form>
      </section>
    </main>
  );
}

function LoginField({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-[10px] font-medium uppercase tracking-[0.1em] text-slate-500">
        {label}
      </span>
      <span className="relative block">
        <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600">
          {icon}
        </span>
        {children}
      </span>
    </label>
  );
}
