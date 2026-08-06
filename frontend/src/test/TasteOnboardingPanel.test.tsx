import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { TasteOnboardingPanel } from '../components/TasteOnboardingPanel';
import { demoPreferenceOptions } from './fixtures/mockData';

describe('TasteOnboardingPanel', () => {
  it('requires three choices and submits positive and negative preferences', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<TasteOnboardingPanel options={demoPreferenceOptions} onSave={onSave} />);
    const saveButton = screen.getByRole('button', { name: 'Zapisz i przejdź do doradcy' });

    expect(saveButton).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Lubię: Thriller' }));
    await user.click(screen.getByRole('button', { name: 'Nie lubię: Komedia' }));
    expect(saveButton).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Lubię: Mroczny klimat' }));
    expect(saveButton).toBeEnabled();

    await user.click(saveButton);
    expect(onSave).toHaveBeenCalledWith(expect.arrayContaining([
      { preferenceType: 'genre', preferenceValue: 'Thriller', polarity: 1 },
      { preferenceType: 'genre', preferenceValue: 'Komedia', polarity: -1 },
      { preferenceType: 'mood', preferenceValue: 'Mroczny klimat', polarity: 1 },
    ]));
  });

  it('switches and removes a choice without counting it twice', async () => {
    const user = userEvent.setup();
    render(<TasteOnboardingPanel options={demoPreferenceOptions} onSave={vi.fn()} />);
    const likesThriller = screen.getByRole('button', { name: 'Lubię: Thriller' });
    const dislikesThriller = screen.getByRole('button', { name: 'Nie lubię: Thriller' });

    await user.click(likesThriller);
    expect(likesThriller).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Wybierz jeszcze 2 pozycje, aby kontynuować.')).toBeInTheDocument();
    await user.click(dislikesThriller);
    expect(likesThriller).toHaveAttribute('aria-pressed', 'false');
    expect(dislikesThriller).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Wybierz jeszcze 2 pozycje, aby kontynuować.')).toBeInTheDocument();
    await user.click(dislikesThriller);
    expect(screen.getByText('Wybierz jeszcze 3 pozycje, aby kontynuować.')).toBeInTheDocument();
  });

  it('requires at least one liked and one disliked choice', async () => {
    const user = userEvent.setup();
    render(<TasteOnboardingPanel options={demoPreferenceOptions} onSave={vi.fn()} />);
    const saveButton = screen.getByRole('button', { name: 'Zapisz i przejdź do doradcy' });

    await user.click(screen.getByRole('button', { name: 'Lubię: Thriller' }));
    await user.click(screen.getByRole('button', { name: 'Lubię: Komedia' }));
    await user.click(screen.getByRole('button', { name: 'Lubię: Mroczny klimat' }));

    expect(saveButton).toBeDisabled();
    expect(
      screen.getByText('Wybierz przynajmniej jedną rzecz, której nie lubisz.'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Nie lubię: Komedia' }));
    expect(saveButton).toBeEnabled();
  });
});
