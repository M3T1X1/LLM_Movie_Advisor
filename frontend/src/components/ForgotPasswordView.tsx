import { Mail } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { AuthField, AuthPage, inputClassName, PrimaryButton } from './auth/AuthForm';

export function ForgotPasswordView({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim()) return setError('Podaj adres e-mail przypisany do konta.');
    setError(null);
    setSent(true);
  };

  return (
    <AuthPage title="Odzyskaj hasło" description="Podaj adres e-mail użyty podczas rejestracji." onBack={onBack}>
      <form onSubmit={submit} className="space-y-5 px-6 py-7 sm:px-8" noValidate>
        <AuthField label="Adres e-mail" icon={<Mail className="h-4 w-4" />}><input type="email" value={email} onChange={(event) => { setEmail(event.target.value); setError(null); setSent(false); }} autoComplete="email" autoFocus maxLength={254} placeholder="Wprowadź e-mail" className={inputClassName} /></AuthField>
        <div className="min-h-10" aria-live="polite">{error && <p className="text-xs text-red-300">{error}</p>}{sent && <p className="text-xs leading-5 text-emerald-300">Jeśli konto istnieje, instrukcja zmiany hasła zostanie wysłana na podany adres.</p>}</div>
        <PrimaryButton>Wyślij instrukcję</PrimaryButton>
      </form>
    </AuthPage>
  );
}
