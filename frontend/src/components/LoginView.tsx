import { Mail } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { AuthField, AuthPage, inputClassName, PasswordField, PrimaryButton } from './auth/AuthForm';

export function LoginView({ onLogin, onRegister }: { onLogin: (email: string, password: string) => Promise<void>; onRegister: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLocaleLowerCase('pl-PL');
    if (!normalizedEmail || !password) return setError('Podaj adres e-mail i hasło.');
    setIsSubmitting(true);
    try {
      await onLogin(normalizedEmail, password);
    } catch {
      setError('Nieprawidłowy adres e-mail lub hasło.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthPage title="Zaloguj się">
      <form onSubmit={submit} className="space-y-5 px-6 py-7 sm:px-8" noValidate>
        <AuthField label="Adres e-mail" icon={<Mail className="h-4 w-4" />}>
          <input type="email" value={email} onChange={(event) => { setEmail(event.target.value); setError(null); }} autoComplete="email" autoFocus maxLength={254} placeholder="Wprowadź e-mail" aria-invalid={Boolean(error)} className={inputClassName} />
        </AuthField>
        <PasswordField label="Hasło" value={password} visible={showPassword} error={error} autoComplete="current-password" onChange={(value) => { setPassword(value); setError(null); }} onToggle={() => setShowPassword((current) => !current)} />
        <div className="min-h-5" aria-live="polite">
          {error && <p className="text-xs text-red-300">{error}</p>}
        </div>
        <PrimaryButton disabled={isSubmitting}>{isSubmitting ? 'Logowanie…' : 'Zaloguj się'}</PrimaryButton>
        <p className="text-center text-xs text-slate-600">Nie masz jeszcze konta?{' '}<button type="button" onClick={onRegister} className="font-medium text-violet-400 transition hover:text-violet-300">Zarejestruj się</button></p>
      </form>
    </AuthPage>
  );
}
