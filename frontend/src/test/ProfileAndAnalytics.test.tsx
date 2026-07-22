import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { demoCatalogContent, demoConversations, demoInteractions, demoPreferences, demoProfile, demoUser } from '../data/mockData';
import { AnalyticsView } from '../components/AnalyticsView';
import { ProfileView } from '../components/ProfileView';

describe('profile and analytics views', () => {
  it('renders profile preferences as read-only values', async () => {
    const user = userEvent.setup();
    render(<ProfileView user={demoUser} semanticProfile={demoProfile} preferences={demoPreferences} conversations={demoConversations} savedCount={1} watchedCount={5} onUpdateUser={vi.fn()} />);
    expect(screen.getByText('Twój gust')).toBeInTheDocument();
    expect(screen.getByText('Thriller')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Edytuj profil' }));
    expect(screen.getAllByRole('textbox')).toHaveLength(2);
    expect(screen.queryByLabelText('Ulubione gatunki')).not.toBeInTheDocument();
  });

  it('updates editable account data', async () => {
    const user = userEvent.setup();
    const onUpdateUser = vi.fn();
    render(<ProfileView user={demoUser} semanticProfile={demoProfile} preferences={demoPreferences} conversations={demoConversations} savedCount={1} watchedCount={5} onUpdateUser={onUpdateUser} />);
    await user.click(screen.getByRole('button', { name: 'Edytuj profil' }));
    const username = screen.getByLabelText('Nazwa użytkownika');
    await user.clear(username);
    await user.type(username, 'nowy-user');
    await user.click(screen.getByRole('button', { name: 'Zapisz zmiany' }));
    expect(onUpdateUser).toHaveBeenCalledWith(expect.objectContaining({ username: 'nowy-user' }));
  });

  it('cancels profile editing without persisting changes', async () => {
    const user = userEvent.setup();
    const onUpdateUser = vi.fn();
    render(<ProfileView user={demoUser} semanticProfile={demoProfile} preferences={demoPreferences} conversations={demoConversations} savedCount={1} watchedCount={5} onUpdateUser={onUpdateUser} />);

    await user.click(screen.getByRole('button', { name: 'Edytuj profil' }));
    await user.clear(screen.getByLabelText('Nazwa użytkownika'));
    await user.type(screen.getByLabelText('Nazwa użytkownika'), 'nie-zapisuj');
    await user.click(screen.getByRole('button', { name: 'Anuluj edycję' }));

    expect(onUpdateUser).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: demoUser.username })).toBeInTheDocument();
    expect(screen.queryByLabelText('Nazwa użytkownika')).not.toBeInTheDocument();
  });

  it('builds analytics from watched interactions', () => {
    render(<AnalyticsView content={demoCatalogContent} interactions={demoInteractions} preferences={demoPreferences} />);
    const expectMetric = (label: string, value: string) => {
      const card = screen.getByText(label).parentElement;
      expect(card).not.toBeNull();
      expect(within(card!).getByText(value)).toBeInTheDocument();
    };

    expectMetric('Obejrzane tytuły', '5');
    expectMetric('Łączny czas', '9 h');
    expectMetric('Średnia ocena TMDB', '8.2');
    expectMetric('Na liście', '1');
    expect(screen.getByRole('img', { name: 'Najczęściej oglądane gatunki' })).toBeInTheDocument();
    expect(screen.getByText('Filmy').parentElement).toHaveTextContent('3');
    expect(screen.getByText('Seriale').parentElement).toHaveTextContent('2');
  });

  it('switches to the taste map and selects a genre', async () => {
    const user = userEvent.setup();
    render(<AnalyticsView content={demoCatalogContent} interactions={demoInteractions} preferences={demoPreferences} />);

    await user.click(screen.getByRole('button', { name: 'Mapa gustu' }));
    expect(screen.getByRole('img', { name: 'Interaktywna mapa gustu' })).toBeInTheDocument();
    const adventureLabel = screen.getByText('Przygodowy');
    const adventureButton = adventureLabel.closest('[role="button"]');
    expect(adventureButton).not.toBeNull();
    fireEvent.click(adventureButton!);

    expect(screen.getByRole('heading', { name: 'Przygodowy' })).toBeInTheDocument();
    expect(screen.getByText('Diuna: Część druga')).toBeInTheDocument();
  });

  it('shows an empty analytics state without watched content', () => {
    render(<AnalyticsView content={demoCatalogContent} interactions={[]} preferences={demoPreferences} />);
    expect(screen.getByText('Brak danych do analizy')).toBeInTheDocument();
  });
});
