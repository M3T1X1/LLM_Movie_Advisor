import { render, screen } from '@testing-library/react';
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

  it('builds analytics from watched interactions', () => {
    render(<AnalyticsView content={demoCatalogContent} interactions={demoInteractions} preferences={demoPreferences} />);
    expect(screen.getByText('Analiza oglądania')).toBeInTheDocument();
    expect(screen.getByText('Obejrzane tytuły')).toBeInTheDocument();
    expect(screen.getByText('Najczęściej oglądane gatunki')).toBeInTheDocument();
  });

  it('shows an empty analytics state without watched content', () => {
    render(<AnalyticsView content={demoCatalogContent} interactions={[]} preferences={demoPreferences} />);
    expect(screen.getByText('Brak danych do analizy')).toBeInTheDocument();
  });
});
