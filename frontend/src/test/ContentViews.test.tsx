import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { demoCandidates, demoCatalogContent } from '../data/mockData';
import { CatalogView } from '../components/CatalogView';
import { MovieDetailModal } from '../components/MovieDetailModal';
import { RecommendationCard } from '../components/RecommendationCard';

describe('content views', () => {
  it('filters catalog by title and media type', async () => {
    const user = userEvent.setup();
    render(<CatalogView content={demoCatalogContent} watchlistedContentIds={[]} watchedContentIds={[]} onOpen={vi.fn()} onWatchlist={vi.fn()} onMarkWatched={vi.fn()} />);
    await user.type(screen.getByPlaceholderText('Szukaj po tytule...'), 'Zaginiona dziewczyna');
    expect(screen.getByText('1 wynik')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Zaginiona dziewczyna' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Seriale' }));
    expect(screen.getByText('Brak pasujących tytułów')).toBeInTheDocument();
  });

  it('calls catalog card actions', async () => {
    const user = userEvent.setup();
    const onWatchlist = vi.fn();
    const onMarkWatched = vi.fn();
    render(<CatalogView content={[demoCatalogContent[0]]} watchlistedContentIds={[]} watchedContentIds={[]} onOpen={vi.fn()} onWatchlist={onWatchlist} onMarkWatched={onMarkWatched} />);
    await user.click(screen.getByRole('button', { name: 'Zapisz' }));
    await user.click(screen.getByRole('button', { name: 'Obejrzyj' }));
    expect(onWatchlist).toHaveBeenCalledWith(demoCatalogContent[0]);
    expect(onMarkWatched).toHaveBeenCalledWith(demoCatalogContent[0]);
  });

  it('renders recommendation-specific score and explanation', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<RecommendationCard candidate={demoCandidates[0]} index={0} isWatchlisted={false} isWatched={false} onOpen={onOpen} onWatchlist={vi.fn()} onMarkWatched={vi.fn()} />);
    expect(screen.getByText('96%')).toBeInTheDocument();
    expect(screen.getByText(/Trafia w Twoją potrzebę/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Szczegóły' }));
    expect(onOpen).toHaveBeenCalledWith(demoCandidates[0]);
  });

  it('shows AI explanation only for a recommendation modal', () => {
    const props = { isWatchlisted: false, isWatched: false, onClose: vi.fn(), onWatchlist: vi.fn(), onMarkWatched: vi.fn() };
    const { rerender } = render(<MovieDetailModal content={demoCandidates[0].content} recommendation={null} {...props} />);
    expect(screen.queryByText('Dlaczego ten tytuł?')).not.toBeInTheDocument();
    rerender(<MovieDetailModal content={demoCandidates[0].content} recommendation={demoCandidates[0]} {...props} />);
    expect(screen.getByText('Dlaczego ten tytuł?')).toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByText('96% dopasowania')).toBeInTheDocument();
  });
});
