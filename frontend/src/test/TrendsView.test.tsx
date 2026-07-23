import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { TrendsView } from '../components/TrendsView';
import { demoCatalogContent, demoRecommendationTrends } from './fixtures/mockData';
import * as api from '../services/api';

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
    expect(screen.getByRole('button', { name: 'Dzisiaj' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/486\s+wyświetleń rekomendacji/)).toBeInTheDocument();
  });

  it('switches trends between week and month', async () => {
    const user = userEvent.setup();
    render(<TrendsView onOpen={vi.fn()} />);
    await screen.findByText('Thriller');

    await user.click(screen.getByRole('button', { name: 'Tydzień' }));
    await waitFor(() => expect(getTrendingTitles()[0]).toBe('Labirynt'));
    expect(screen.getByRole('button', { name: 'Tydzień' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/3154\s+wyświetleń rekomendacji/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Miesiąc' }));
    await waitFor(() => expect(getTrendingTitles()[0]).toBe('Diuna: Część druga'));
    expect(screen.getByRole('button', { name: 'Miesiąc' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Tydzień' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('opens movie details from a trend card', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<TrendsView onOpen={onOpen} />);

    await user.click(await screen.findByRole('button', { name: 'Pokaż szczegóły: Zaginiona dziewczyna' }));
    expect(onOpen).toHaveBeenCalledWith(demoCatalogContent[0]);
  });

  it('shows an API error and retries loading trends', async () => {
    const user = userEvent.setup();
    const trendsRequest = vi
      .spyOn(api, 'getRecommendationTrends')
      .mockRejectedValueOnce(new Error('Brak połączenia'))
      .mockResolvedValueOnce(demoRecommendationTrends.day);
    render(<TrendsView onOpen={vi.fn()} />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Nie udało się pobrać trendów');
    await user.click(screen.getByRole('button', { name: 'Spróbuj ponownie' }));
    expect(await screen.findByText('Thriller')).toBeInTheDocument();
    expect(trendsRequest).toHaveBeenNthCalledWith(1, 'day');
    expect(trendsRequest).toHaveBeenNthCalledWith(2, 'day');
  });
});
