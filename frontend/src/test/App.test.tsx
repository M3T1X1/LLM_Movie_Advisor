import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
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
    ['/catalog', 'Baza filmów i seriali'],
    ['/trends', 'Trendy'],
    ['/upcoming', 'Przyszłe premiery'],
    ['/watchlist', 'Zapisane na później'],
    ['/analytics', 'Analiza oglądania'],
    ['/profile', 'kacper'],
    ['/recommendations', 'Dzień dobry, kacper'],
  ])('renders %s route', async (path, heading) => {
    renderApp(path);
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
  });

  it('updates URL when navigating from navbar', async () => {
    const user = userEvent.setup();
    renderApp('/recommendations');
    await user.click(await screen.findByRole('button', { name: /Baza filmów i seriali/i }));
    await waitFor(() => expect(window.location.pathname).toBe('/catalog'));
    expect(screen.getByText('Katalog TMDB')).toBeInTheDocument();
  });

  it('moves from backend login to recommendations', async () => {
    const user = userEvent.setup();
    renderApp('/login');
    await user.type(await screen.findByLabelText('Adres e-mail'), 'user@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'haslo123');
    await user.click(screen.getByRole('button', { name: 'Zaloguj się' }));
    expect(window.location.pathname).toBe('/recommendations');
    expect(screen.getByRole('heading', { name: 'Dzień dobry, kacper' })).toBeInTheDocument();
  });

  it('clearly reports that recommendations are not active yet', async () => {
    renderApp('/recommendations');
    expect(
      await screen.findByText('System rekomendacji nie jest jeszcze aktywny'),
    ).toBeInTheDocument();
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
  });

  it('falls back to login for an unknown route', async () => {
    renderApp('/nie-istnieje');
    expect(
      await screen.findByRole('heading', { name: 'Zaloguj się' }),
    ).toBeInTheDocument();
  });

  it('protects application routes when backend session is anonymous', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ authenticated: false, user: null }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    renderApp('/catalog');

    expect(
      await screen.findByRole('heading', { name: 'Zaloguj się' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/login');
  });

  it('registers an account through backend and opens the application', async () => {
    const user = userEvent.setup();
    renderApp('/register');

    await user.type(await screen.findByLabelText('Nazwa użytkownika'), 'new-user');
    await user.type(screen.getByLabelText('Adres e-mail'), 'new@example.com');
    await user.type(screen.getByLabelText('Hasło'), 'StrongPassword123!');
    await user.type(screen.getByLabelText('Powtórz hasło'), 'StrongPassword123!');
    await user.click(screen.getByRole('button', { name: 'Utwórz konto' }));

    expect(
      await screen.findByRole('heading', { name: 'Dzień dobry, kacper' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/recommendations');
  });

  it('reacts to browser back and forward navigation', async () => {
    renderApp('/catalog');
    window.history.pushState({}, '', '/trends');
    window.dispatchEvent(new PopStateEvent('popstate'));

    expect(await screen.findByRole('heading', { name: 'Trendy' })).toBeInTheDocument();
  });

  it('persists a prompt without fabricating recommendations', async () => {
    const user = userEvent.setup();
    renderApp('/recommendations');

    await user.click(
      await screen.findByRole('button', { name: 'Lekki serial na dwa wieczory' }),
    );
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText('Opisz nastrój, tempo albo motyw...')).toHaveValue(
      'Lekki serial na dwa wieczory',
    );

    await user.click(screen.getByRole('button', { name: 'Wyślij wiadomość' }));
    expect(
      (await screen.findAllByText('Lekki serial na dwa wieczory')).length,
    ).toBeGreaterThanOrEqual(2);
    expect(
      screen.getByText('System rekomendacji nie jest jeszcze aktywny'),
    ).toBeInTheDocument();
    expect(screen.queryByText('96%')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Nowa rozmowa' }));
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
  });

  it('adds and removes a catalog title from the saved view', async () => {
    const user = userEvent.setup();
    renderApp('/catalog');
    const labiryntCard = (await screen.findByRole('heading', { name: 'Labirynt' })).closest('article');
    expect(labiryntCard).not.toBeNull();

    await user.click(within(labiryntCard!).getByRole('button', { name: 'Zapisz' }));
    await user.click(screen.getByRole('button', { name: /Menu użytkownika:/ }));
    await user.click(screen.getByRole('menuitem', { name: 'Moja lista' }));
    expect(window.location.pathname).toBe('/watchlist');
    expect(screen.getByRole('heading', { name: 'Labirynt' })).toBeInTheDocument();

    const savedLabiryntCard = screen.getByRole('heading', { name: 'Labirynt' }).closest('article');
    await user.click(within(savedLabiryntCard!).getByRole('button', { name: 'Zapisano' }));
    expect(screen.queryByRole('heading', { name: 'Labirynt' })).not.toBeInTheDocument();
  });

  it('keeps a saved upcoming release available in the watchlist', async () => {
    const user = userEvent.setup();
    renderApp('/upcoming');
    const releaseHeading = await screen.findByRole('heading', { name: 'Ostatni sygnał' });
    const releaseCard = releaseHeading.closest('article');
    expect(releaseCard).not.toBeNull();

    await user.click(within(releaseCard!).getByRole('button', { name: 'Zapisz na listę' }));
    await user.click(screen.getByRole('button', { name: /Menu użytkownika:/ }));
    await user.click(screen.getByRole('menuitem', { name: 'Moja lista' }));

    expect(window.location.pathname).toBe('/watchlist');
    expect(screen.getByRole('heading', { name: 'Ostatni sygnał' })).toBeInTheDocument();
  });

  it('logs out from the avatar menu and returns to login', async () => {
    const user = userEvent.setup();
    renderApp('/recommendations');

    await user.click(await screen.findByRole('button', { name: /Menu użytkownika:/ }));
    await user.click(screen.getByRole('menuitem', { name: 'Wyloguj się' }));

    expect(window.location.pathname).toBe('/login');
    expect(screen.getByRole('heading', { name: 'Zaloguj się' })).toBeInTheDocument();
  });
});
