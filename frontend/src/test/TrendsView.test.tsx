import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { TrendsView } from '../components/TrendsView';
import { demoCatalogContent } from '../data/mockData';

function getTrendingTitles() {
  const heading = screen.getByRole('heading', { name: 'Najczęściej wyświetlane filmy' });
  const section = heading.closest('section');
  if (!section) throw new Error('Nie znaleziono sekcji trendujących filmów.');
  return within(section).getAllByRole('heading', { level: 3 }).map((item) => item.textContent);
}

describe('TrendsView', () => {
  it('shows recommended genres and the daily top three in descending order', async () => {
    render(<TrendsView onOpen={vi.fn()} />);

    expect(await screen.findByText('Thriller')).toBeInTheDocument();
    expect(screen.getByText('Dramat')).toBeInTheDocument();
    expect(getTrendingTitles()).toEqual([
      'Zaginiona dziewczyna',
      'Labirynt',
      'To nie jest kraj dla starych ludzi',
    ]);
    expect(screen.getByLabelText('Pozycja: 1')).toBeInTheDocument();
    expect(screen.getByLabelText('Pozycja: 3')).toBeInTheDocument();
  });

  it('switches trends between week and month', async () => {
    const user = userEvent.setup();
    render(<TrendsView onOpen={vi.fn()} />);
    await screen.findByText('Thriller');

    await user.click(screen.getByRole('button', { name: 'Tydzień' }));
    await waitFor(() => expect(getTrendingTitles()[0]).toBe('Labirynt'));
    expect(screen.getByText('Dane za ostatnie 7 dni')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Miesiąc' }));
    await waitFor(() => expect(getTrendingTitles()[0]).toBe('Diuna: Część druga'));
    expect(screen.getByText('Dane za ostatnie 30 dni')).toBeInTheDocument();
  });

  it('opens movie details from a trend card', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<TrendsView onOpen={onOpen} />);

    await user.click(await screen.findByRole('button', { name: 'Pokaż szczegóły: Zaginiona dziewczyna' }));
    expect(onOpen).toHaveBeenCalledWith(demoCatalogContent[0]);
  });
});
