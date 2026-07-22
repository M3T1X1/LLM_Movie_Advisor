import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../App';
import { SessionProvider } from '../context/SessionContext';

function renderApp(path: string) {
  window.history.replaceState({}, '', path);
  return render(<SessionProvider><App /></SessionProvider>);
}

describe('App routing', () => {
  beforeEach(() => window.history.replaceState({}, '', '/'));

  it.each([
    ['/login', 'Zaloguj się'],
    ['/register', 'Utwórz konto'],
    ['/forgot-password', 'Odzyskaj hasło'],
    ['/catalog', 'Baza filmów i seriali'],
    ['/watchlist', 'Zapisane na później'],
    ['/analytics', 'Analiza oglądania'],
    ['/profile', 'Konto użytkownika'],
    ['/recommendations', 'Co masz ochotę dziś obejrzeć?'],
  ])('renders %s route', async (path, heading) => {
    renderApp(path);
    expect((await screen.findAllByText(heading)).length).toBeGreaterThan(0);
  });

  it('updates URL when navigating from navbar', async () => {
    const user = userEvent.setup();
    renderApp('/recommendations');
    await user.click(screen.getByRole('button', { name: /Baza filmów i seriali/i }));
    await waitFor(() => expect(window.location.pathname).toBe('/catalog'));
    expect(screen.getByText('Katalog TMDB')).toBeInTheDocument();
  });

  it('moves from valid mock login to recommendations', async () => {
    const user = userEvent.setup();
    renderApp('/login');
    await user.type(screen.getByLabelText('Adres e-mail'), 'user@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'haslo123');
    await user.click(screen.getByRole('button', { name: 'Zaloguj się' }));
    expect(window.location.pathname).toBe('/recommendations');
    expect(screen.getByText('Co masz ochotę dziś obejrzeć?')).toBeInTheDocument();
  });

  it('does not show recommendations before the user sends a prompt', () => {
    renderApp('/recommendations');
    expect(screen.getByText('Brak rekomendacji w tej rozmowie')).toBeInTheDocument();
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
  });
});
