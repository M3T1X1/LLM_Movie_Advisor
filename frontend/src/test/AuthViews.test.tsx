import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ForgotPasswordView } from '../components/ForgotPasswordView';
import { LoginView } from '../components/LoginView';
import { RegisterView } from '../components/RegisterView';

describe('authentication views', () => {
  it('validates and submits login credentials', async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    render(<LoginView onLogin={onLogin} onRegister={vi.fn()} onForgotPassword={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Zaloguj się' }));
    expect(screen.getByText('Podaj adres e-mail i hasło.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Adres e-mail'), 'USER@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'sekret123');
    await user.click(screen.getByRole('button', { name: 'Zaloguj się' }));
    expect(onLogin).toHaveBeenCalledWith('user@example.com', 'sekret123');
  });

  it('links login to registration and password recovery', async () => {
    const user = userEvent.setup();
    const onRegister = vi.fn();
    const onForgotPassword = vi.fn();
    render(<LoginView onLogin={vi.fn()} onRegister={onRegister} onForgotPassword={onForgotPassword} />);
    await user.click(screen.getByRole('button', { name: 'Zarejestruj się' }));
    await user.click(screen.getByRole('button', { name: 'Nie pamiętasz hasła?' }));
    expect(onRegister).toHaveBeenCalledOnce();
    expect(onForgotPassword).toHaveBeenCalledOnce();
  });

  it('toggles password visibility without submitting the login form', async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    render(<LoginView onLogin={onLogin} onRegister={vi.fn()} onForgotPassword={vi.fn()} />);
    const password = screen.getByLabelText('Hasło');

    expect(password).toHaveAttribute('type', 'password');
    await user.click(screen.getByRole('button', { name: 'Pokaż hasło' }));
    expect(password).toHaveAttribute('type', 'text');
    expect(onLogin).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Ukryj hasło' }));
    expect(password).toHaveAttribute('type', 'password');
  });

  it('checks password confirmation during registration', async () => {
    const user = userEvent.setup();
    const onRegistered = vi.fn();
    render(<RegisterView onBack={vi.fn()} onRegistered={onRegistered} />);
    await user.type(screen.getByLabelText('Nazwa użytkownika'), 'tester');
    await user.type(screen.getByLabelText('Adres e-mail'), 'tester@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'haslo123');
    await user.type(screen.getByLabelText('Powtórz hasło'), 'innehaslo');
    await user.click(screen.getByRole('button', { name: 'Utwórz konto' }));
    expect(screen.getByText('Podane hasła nie są takie same.')).toBeInTheDocument();
    expect(onRegistered).not.toHaveBeenCalled();
  });

  it('rejects incomplete registration and a password shorter than eight characters', async () => {
    const user = userEvent.setup();
    const onRegistered = vi.fn();
    render(<RegisterView onBack={vi.fn()} onRegistered={onRegistered} />);

    await user.click(screen.getByRole('button', { name: 'Utwórz konto' }));
    expect(screen.getByText('Uzupełnij wszystkie pola.')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Nazwa użytkownika'), 'tester');
    await user.type(screen.getByLabelText('Adres e-mail'), 'tester@example.com');
    await user.type(screen.getByLabelText('Hasło'), '1234567');
    await user.type(screen.getByLabelText('Powtórz hasło'), '1234567');
    await user.click(screen.getByRole('button', { name: 'Utwórz konto' }));
    expect(screen.getByText('Hasło musi zawierać co najmniej 8 znaków.')).toBeInTheDocument();
    expect(onRegistered).not.toHaveBeenCalled();
  });

  it('submits a valid registration using schema-compatible fields', async () => {
    const user = userEvent.setup();
    const onRegistered = vi.fn();
    render(<RegisterView onBack={vi.fn()} onRegistered={onRegistered} />);
    await user.type(screen.getByLabelText('Nazwa użytkownika'), 'tester');
    await user.type(screen.getByLabelText('Adres e-mail'), 'TEST@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'haslo123');
    await user.type(screen.getByLabelText('Powtórz hasło'), 'haslo123');
    await user.click(screen.getByRole('button', { name: 'Utwórz konto' }));
    expect(onRegistered).toHaveBeenCalledWith(
      'tester',
      'test@example.com',
      'haslo123',
    );
  });

  it('shows a neutral password reset confirmation', async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordView onBack={vi.fn()} />);
    await user.type(screen.getByLabelText('Adres e-mail'), 'unknown@example.com');
    await user.click(screen.getByRole('button', { name: 'Wyślij instrukcję' }));
    expect(screen.getByText(/Jeśli konto istnieje/)).toBeInTheDocument();
  });

  it('validates password reset and returns to login', async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<ForgotPasswordView onBack={onBack} />);

    await user.click(screen.getByRole('button', { name: 'Wyślij instrukcję' }));
    expect(screen.getByText('Podaj adres e-mail przypisany do konta.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Wróć do logowania' }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});
