import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { UpcomingReleasesView } from '../components/UpcomingReleasesView';
import { demoUpcomingReleases } from './fixtures/mockData';

const defaultProps = {
  watchlistedContentIds: [],
  onOpen: vi.fn(),
  onWatchlist: vi.fn(),
  onLoaded: vi.fn(),
};

describe('UpcomingReleasesView', () => {
  it('shows upcoming movies chronologically with descriptions and release dates', async () => {
    const onLoaded = vi.fn();
    render(<UpcomingReleasesView {...defaultProps} onLoaded={onLoaded} />);

    await screen.findByRole('heading', { name: 'Ostatni sygnał' });
    const region = screen.getByRole('region', { name: 'Nadchodzące filmy' });
    const movieHeadings = within(region).getAllByRole('heading', { level: 2 }).slice(1);

    expect(movieHeadings.map((heading) => heading.textContent)).toEqual(
      demoUpcomingReleases.map((item) => item.title),
    );
    expect(screen.getByText(/Załoga stacji badawczej/)).toBeInTheDocument();
    expect(region.querySelectorAll('time')).toHaveLength(demoUpcomingReleases.length);
    expect(onLoaded).toHaveBeenCalledWith(demoUpcomingReleases);
  });

  it('combines title, genre and date-range filters and clears them', async () => {
    const user = userEvent.setup();
    render(<UpcomingReleasesView {...defaultProps} />);
    await screen.findByRole('heading', { name: 'Ostatni sygnał' });

    await user.selectOptions(screen.getByLabelText('Zakres czasu'), '30');
    expect(screen.getByText('2 premiery')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Gatunek'), 'Science Fiction');
    expect(screen.getByText('1 premiera')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Ostatni sygnał' })).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText('Szukaj po tytule...'), 'nieistniejący');
    expect(screen.getByText('Brak premier dla tych filtrów')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Wyczyść filtry' }));
    expect(screen.getByText(`${demoUpcomingReleases.length} premier`)).toBeInTheDocument();
    expect(screen.getByLabelText('Gatunek')).toHaveValue('all');
    expect(screen.getByLabelText('Zakres czasu')).toHaveValue('all');
  });

  it('filters releases by their month', async () => {
    const user = userEvent.setup();
    render(<UpcomingReleasesView {...defaultProps} />);
    await screen.findByRole('heading', { name: 'Ostatni sygnał' });
    const firstMonth = demoUpcomingReleases[0].releaseDate!.slice(0, 7);

    await user.selectOptions(screen.getByLabelText('Miesiąc premiery'), firstMonth);

    const releasesInMonth = demoUpcomingReleases.filter((item) =>
      item.releaseDate?.startsWith(firstMonth),
    );
    const countLabel = releasesInMonth.length === 1
      ? '1 premiera'
      : releasesInMonth.length >= 2 && releasesInMonth.length <= 4
        ? `${releasesInMonth.length} premiery`
        : `${releasesInMonth.length} premier`;
    expect(screen.getByText(countLabel)).toBeInTheDocument();
    releasesInMonth.forEach((item) => {
      expect(screen.getByRole('heading', { name: item.title })).toBeInTheDocument();
    });
  });

  it('opens details and saves a release', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const onWatchlist = vi.fn();
    render(
      <UpcomingReleasesView
        {...defaultProps}
        onOpen={onOpen}
        onWatchlist={onWatchlist}
      />,
    );
    const heading = await screen.findByRole('heading', { name: 'Ostatni sygnał' });
    const card = heading.closest('article');
    expect(card).not.toBeNull();

    await user.click(within(card!).getByRole('button', { name: 'Pokaż szczegóły: Ostatni sygnał' }));
    await user.click(within(card!).getByRole('button', { name: 'Zapisz na listę' }));

    expect(onOpen).toHaveBeenCalledWith(demoUpcomingReleases[0]);
    expect(onWatchlist).toHaveBeenCalledWith(demoUpcomingReleases[0]);
  });
});
