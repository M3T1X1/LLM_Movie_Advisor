import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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
    ['/forgot-password', 'Odzyskaj hasło'],
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
    expect(screen.getByRole('heading', { name: 'Dzień dobry, kacper' })).toBeInTheDocument();
  });

  it('does not show recommendations before the user sends a prompt', () => {
    renderApp('/recommendations');
    expect(screen.getByText('Brak rekomendacji w tej rozmowie')).toBeInTheDocument();
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
  });

  it('falls back to login for an unknown route', () => {
    renderApp('/nie-istnieje');
    expect(screen.getByRole('heading', { name: 'Zaloguj się' })).toBeInTheDocument();
  });

  it('reacts to browser back and forward navigation', async () => {
    renderApp('/catalog');
    window.history.pushState({}, '', '/trends');
    window.dispatchEvent(new PopStateEvent('popstate'));

    expect(await screen.findByRole('heading', { name: 'Trendy' })).toBeInTheDocument();
  });

  it('generates recommendations only after explicitly sending a prompt', async () => {
    vi.useFakeTimers();
    renderApp('/recommendations');

    fireEvent.click(screen.getByRole('button', { name: 'Lekki serial na dwa wieczory' }));
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText('Opisz nastrój, tempo albo motyw...')).toHaveValue(
      'Lekki serial na dwa wieczory',
    );

    fireEvent.click(screen.getByRole('button', { name: 'Wyślij wiadomość' }));
    expect(screen.getByText('Analizuję Twój prompt…')).toBeInTheDocument();

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText('96%')).toBeInTheDocument();
    expect(screen.getByText('93%')).toBeInTheDocument();
    expect(screen.getByText('89%')).toBeInTheDocument();
    expect(screen.getByText(/Znalazłem trzy historie/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Nowa rozmowa' }));
    expect(screen.getByText('Brak rekomendacji w tej rozmowie')).toBeInTheDocument();
    expect(screen.queryByText('96%')).not.toBeInTheDocument();
  });

  it('adds and removes a catalog title from the saved view', async () => {
    const user = userEvent.setup();
    renderApp('/catalog');
    const labiryntCard = screen.getByRole('heading', { name: 'Labirynt' }).closest('article');
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

    await user.click(screen.getByRole('button', { name: /Menu użytkownika:/ }));
    await user.click(screen.getByRole('menuitem', { name: 'Wyloguj się' }));

    expect(window.location.pathname).toBe('/login');
    expect(screen.getByRole('heading', { name: 'Zaloguj się' })).toBeInTheDocument();
  });
});
