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

  it('submits a valid registration using schema-compatible fields', async () => {
    const user = userEvent.setup();
    const onRegistered = vi.fn();
    render(<RegisterView onBack={vi.fn()} onRegistered={onRegistered} />);
    await user.type(screen.getByLabelText('Nazwa użytkownika'), 'tester');
    await user.type(screen.getByLabelText('Adres e-mail'), 'TEST@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'haslo123');
    await user.type(screen.getByLabelText('Powtórz hasło'), 'haslo123');
    await user.click(screen.getByRole('button', { name: 'Utwórz konto' }));
    expect(onRegistered).toHaveBeenCalledWith('test@example.com');
  });

  it('shows a neutral password reset confirmation', async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordView onBack={vi.fn()} />);
    await user.type(screen.getByLabelText('Adres e-mail'), 'unknown@example.com');
    await user.click(screen.getByRole('button', { name: 'Wyślij instrukcję' }));
    expect(screen.getByText(/Jeśli konto istnieje/)).toBeInTheDocument();
  });
});
