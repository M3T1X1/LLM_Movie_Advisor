import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { demoCandidates, demoCatalogContent } from '../data/mockData';
import { CatalogView } from '../components/CatalogView';
import { MovieDetailModal } from '../components/MovieDetailModal';
import { RecommendationCard } from '../components/RecommendationCard';

describe('content views', () => {
  const catalogProps = {
    content: demoCatalogContent,
    watchlistedContentIds: [],
    watchedContentIds: [],
    onOpen: vi.fn(),
    onWatchlist: vi.fn(),
    onMarkWatched: vi.fn(),
  };

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

  it('combines catalog filters and restores the full catalog', async () => {
    const user = userEvent.setup();
    render(<CatalogView {...catalogProps} />);

    await user.click(screen.getByRole('button', { name: 'Filmy' }));
    await user.selectOptions(screen.getByLabelText('Gatunek'), 'Dramat');
    await user.selectOptions(screen.getByLabelText('Minimalna ocena'), '8');
    await user.type(screen.getByPlaceholderText('np. 2015'), '2014');

    expect(screen.getByText('2 wyników')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Zaginiona dziewczyna' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Diuna: Część druga' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Labirynt' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Wyczyść filtry' }));
    expect(screen.getByText('6 wyników')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('np. 2015')).toHaveValue(null);
    expect(screen.getByLabelText('Gatunek')).toHaveValue('all');
  });

  it('sorts catalog content by rating and release date', async () => {
    const user = userEvent.setup();
    render(<CatalogView {...catalogProps} />);

    await user.selectOptions(screen.getByLabelText('Sortowanie'), 'rating');
    expect(screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)).toEqual([
      'Dark',
      'Labirynt',
      'The Bear',
      'Zaginiona dziewczyna',
      'Diuna: Część druga',
      'To nie jest kraj dla starych ludzi',
    ]);

    await user.selectOptions(screen.getByLabelText('Sortowanie'), 'newest');
    expect(screen.getAllByRole('heading', { level: 2 })[0]).toHaveTextContent('Diuna: Część druga');
  });

  it('opens a catalog item and renders active card states', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(
      <CatalogView
        content={[demoCatalogContent[0]]}
        watchlistedContentIds={[demoCatalogContent[0].id]}
        watchedContentIds={[demoCatalogContent[0].id]}
        onOpen={onOpen}
        onWatchlist={vi.fn()}
        onMarkWatched={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: 'Zapisano' })).toHaveAttribute('title', 'Usuń z listy');
    expect(screen.getByRole('button', { name: 'Obejrzano' })).toHaveAttribute(
      'title',
      'Cofnij oznaczenie jako obejrzany',
    );
    await user.click(screen.getByRole('button', { name: 'Pokaż szczegóły: Zaginiona dziewczyna' }));
    expect(onOpen).toHaveBeenCalledWith(demoCatalogContent[0]);
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

  it('calls recommendation actions and reflects their active state', async () => {
    const user = userEvent.setup();
    const onWatchlist = vi.fn();
    const onMarkWatched = vi.fn();
    render(
      <RecommendationCard
        candidate={demoCandidates[0]}
        index={0}
        isWatchlisted
        isWatched
        onOpen={vi.fn()}
        onWatchlist={onWatchlist}
        onMarkWatched={onMarkWatched}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Zapisano' }));
    await user.click(screen.getByRole('button', { name: 'Obejrzano' }));
    expect(onWatchlist).toHaveBeenCalledWith(demoCandidates[0]);
    expect(onMarkWatched).toHaveBeenCalledWith(demoCandidates[0]);
  });

  it('shows AI explanation only for a recommendation modal', () => {
    const props = { isWatchlisted: false, isWatched: false, onClose: vi.fn(), onWatchlist: vi.fn(), onMarkWatched: vi.fn() };
    const { rerender } = render(<MovieDetailModal content={demoCandidates[0].content} recommendation={null} {...props} />);
    expect(screen.queryByText('Dlaczego ten tytuł?')).not.toBeInTheDocument();
    rerender(<MovieDetailModal content={demoCandidates[0].content} recommendation={demoCandidates[0]} {...props} />);
    expect(screen.getByText('Dlaczego ten tytuł?')).toBeInTheDocument();
    expect(within(screen.getByRole('dialog')).getByText('96% dopasowania')).toBeInTheDocument();
  });

  it('supports modal actions, Escape, backdrop closing and body scroll lock', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onWatchlist = vi.fn();
    const onMarkWatched = vi.fn();
    const props = {
      recommendation: null,
      isWatchlisted: false,
      isWatched: false,
      onClose,
      onWatchlist,
      onMarkWatched,
    };
    const { rerender } = render(
      <MovieDetailModal content={demoCandidates[0].content} {...props} />,
    );

    expect(document.body).toHaveClass('overflow-hidden');
    await user.click(screen.getByRole('button', { name: 'Zapisz' }));
    await user.click(screen.getByRole('button', { name: 'Oznacz jako obejrzany' }));
    expect(onWatchlist).toHaveBeenCalledOnce();
    expect(onMarkWatched).toHaveBeenCalledOnce();

    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledOnce();
    fireEvent.mouseDown(screen.getByRole('dialog'));
    expect(onClose).toHaveBeenCalledTimes(2);

    rerender(<MovieDetailModal content={null} {...props} />);
    expect(document.body).not.toHaveClass('overflow-hidden');
  });
});
