import { Mail, UserRound } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { AuthField, AuthPage, inputClassName, PasswordField, PrimaryButton } from './auth/AuthForm';

export function RegisterView({ onBack, onRegistered }: { onBack: () => void; onRegistered: (username: string, email: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLocaleLowerCase('pl-PL');
    if (!username.trim() || !normalizedEmail || !password || !confirmation) return setError('Uzupełnij wszystkie pola.');
    if (password.length < 8) return setError('Hasło musi zawierać co najmniej 8 znaków.');
    if (password !== confirmation) return setError('Podane hasła nie są takie same.');
    setIsSubmitting(true);
    try {
      await onRegistered(username.trim(), normalizedEmail, password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Nie udało się utworzyć konta.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthPage title="Utwórz konto" onBack={onBack}>
      <form onSubmit={submit} className="space-y-4 px-6 py-7 sm:px-8" noValidate>
        <AuthField label="Nazwa użytkownika" icon={<UserRound className="h-4 w-4" />}><input type="text" value={username} onChange={(event) => { setUsername(event.target.value); setError(null); }} autoComplete="username" autoFocus maxLength={150} placeholder="Wybierz nazwę użytkownika" className={inputClassName} /></AuthField>
        <AuthField label="Adres e-mail" icon={<Mail className="h-4 w-4" />}><input type="email" value={email} onChange={(event) => { setEmail(event.target.value); setError(null); }} autoComplete="email" maxLength={254} placeholder="Wprowadź e-mail" className={inputClassName} /></AuthField>
        <PasswordField label="Hasło" value={password} visible={showPassword} error={error} autoComplete="new-password" onChange={(value) => { setPassword(value); setError(null); }} onToggle={() => setShowPassword((current) => !current)} />
        <PasswordField label="Powtórz hasło" value={confirmation} visible={showPassword} error={error} autoComplete="new-password" onChange={(value) => { setConfirmation(value); setError(null); }} />
        <div className="min-h-5" aria-live="polite">{error && <p className="text-xs text-red-300">{error}</p>}</div>
        <PrimaryButton disabled={isSubmitting}>{isSubmitting ? 'Tworzenie konta…' : 'Utwórz konto'}</PrimaryButton>
      </form>
    </AuthPage>
  );
}
