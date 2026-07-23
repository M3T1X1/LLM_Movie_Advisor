import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { demoCandidates, demoCatalogContent } from './fixtures/mockData';
import { CatalogView } from '../components/CatalogView';
import { MovieDetailModal } from '../components/MovieDetailModal';
import { RecommendationCard } from '../components/RecommendationCard';
import type { CatalogQuery } from '../types';

describe('content views', () => {
  const initialQuery: CatalogQuery = {
    page: 1,
    pageSize: 20,
    search: '',
    mediaType: 'all',
    genre: 'all',
    minimumRating: 0,
    yearFrom: null,
    sortBy: 'popularity',
  };
  const catalogProps = {
    content: demoCatalogContent,
    genres: ['Dramat', 'Science Fiction', 'Thriller'],
    pagination: {
      page: 1,
      pageSize: 20,
      totalItems: demoCatalogContent.length,
      totalPages: 1,
      hasPrevious: false,
      hasNext: false,
    },
    query: initialQuery,
    isLoading: false,
    error: null,
    onQueryChange: vi.fn(),
    watchlistedContentIds: [],
    watchedContentIds: [],
    onOpen: vi.fn(),
    onWatchlist: vi.fn(),
    onMarkWatched: vi.fn(),
  };

  function CatalogHarness({
    totalPages = 1,
  }: {
    totalPages?: number;
  }) {
    const [query, setQuery] = useState(initialQuery);
    return (
      <CatalogView
        {...catalogProps}
        query={query}
        onQueryChange={setQuery}
        pagination={{
          ...catalogProps.pagination,
          page: query.page,
          totalPages,
          hasPrevious: query.page > 1,
          hasNext: query.page < totalPages,
        }}
      />
    );
  }

  it('maps search and media filters to the server query', async () => {
    const user = userEvent.setup();
    render(<CatalogHarness />);

    await user.type(screen.getByPlaceholderText('Szukaj po tytule...'), 'Zaginiona dziewczyna');
    await new Promise((resolve) => window.setTimeout(resolve, 350));
    await user.click(screen.getByRole('button', { name: 'Seriale' }));

    expect(screen.getByPlaceholderText('Szukaj po tytule...')).toHaveValue(
      'Zaginiona dziewczyna',
    );
    expect(screen.getByRole('button', { name: 'Seriale' })).toHaveClass('text-white');
  });

  it('calls catalog card actions', async () => {
    const user = userEvent.setup();
    const onWatchlist = vi.fn();
    const onMarkWatched = vi.fn();
    render(
      <CatalogView
        {...catalogProps}
        content={[demoCatalogContent[0]]}
        onWatchlist={onWatchlist}
        onMarkWatched={onMarkWatched}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Zapisz' }));
    await user.click(screen.getByRole('button', { name: 'Obejrzyj' }));
    expect(onWatchlist).toHaveBeenCalledWith(demoCatalogContent[0]);
    expect(onMarkWatched).toHaveBeenCalledWith(demoCatalogContent[0]);
  });

  it('combines catalog filters and clears them', async () => {
    const user = userEvent.setup();
    render(<CatalogHarness />);

    await user.click(screen.getByRole('button', { name: 'Filmy' }));
    await user.selectOptions(screen.getByLabelText('Gatunek'), 'Dramat');
    await user.selectOptions(screen.getByLabelText('Minimalna ocena'), '8');
    await user.type(screen.getByPlaceholderText('np. 2015'), '2014');

    expect(screen.getByRole('button', { name: 'Filmy' })).toHaveClass('text-white');
    expect(screen.getByLabelText('Gatunek')).toHaveValue('Dramat');
    expect(screen.getByLabelText('Minimalna ocena')).toHaveValue('8');
    expect(screen.getByPlaceholderText('np. 2015')).toHaveValue(2014);

    await user.click(screen.getByRole('button', { name: 'Wyczyść filtry' }));
    expect(screen.getByPlaceholderText('np. 2015')).toHaveValue(null);
    expect(screen.getByLabelText('Gatunek')).toHaveValue('all');
  });

  it('changes server-side sorting and navigates between pages', async () => {
    const user = userEvent.setup();
    render(<CatalogHarness totalPages={3} />);

    await user.selectOptions(screen.getByLabelText('Sortowanie'), 'rating');
    expect(screen.getByLabelText('Sortowanie')).toHaveValue('rating');

    await user.click(screen.getByRole('button', { name: 'Następna' }));
    expect(screen.getByRole('button', { name: 'Strona 2' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByText('Strona 2 z 3')).toBeInTheDocument();
  });

  it('opens a catalog item and renders active card states', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(
      <CatalogView
        {...catalogProps}
        content={[demoCatalogContent[0]]}
        onOpen={onOpen}
        watchlistedContentIds={[demoCatalogContent[0].id]}
        watchedContentIds={[demoCatalogContent[0].id]}
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
