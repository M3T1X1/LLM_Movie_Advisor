import { Clapperboard, Sparkles, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import type {
  MoviePreferenceOption,
  MoviePreferenceOptions,
  MoviePreferenceSelection,
} from '../types';

interface TasteOnboardingPanelProps {
  options: MoviePreferenceOptions;
  onSave: (preferences: MoviePreferenceSelection[]) => Promise<void> | void;
}

const minimumSelectionCount = 3;

function choiceKey(preferenceType: string, preferenceValue: string) {
  return JSON.stringify([preferenceType, preferenceValue]);
}

export function TasteOnboardingPanel({ options, onSave }: TasteOnboardingPanelProps) {
  const [selections, setSelections] = useState<Map<string, MoviePreferenceSelection>>(
    () => new Map(),
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const selectionCount = selections.size;
  const likedCount = Array.from(selections.values()).filter(
    (selection) => selection.polarity === 1,
  ).length;
  const dislikedCount = selectionCount - likedCount;
  const remainingCount = Math.max(0, minimumSelectionCount - selectionCount);
  const canSave =
    selectionCount >= minimumSelectionCount && likedCount > 0 && dislikedCount > 0;

  const select = (
    preferenceType: string,
    preferenceValue: string,
    polarity: -1 | 1,
  ) => {
    const key = choiceKey(preferenceType, preferenceValue);
    setSaveError(null);
    setSelections((current) => {
      const next = new Map(current);
      const existing = next.get(key);
      if (existing?.polarity === polarity) {
        next.delete(key);
      } else {
        next.set(key, { preferenceType, preferenceValue, polarity });
      }
      return next;
    });
  };

  const save = async () => {
    if (!canSave || isSaving) return;
    setSaveError(null);
    setIsSaving(true);
    try {
      await onSave(Array.from(selections.values()));
    } catch (reason) {
      setSaveError(
        reason instanceof Error
          ? reason.message
          : 'Nie udało się zapisać upodobań. Spróbuj ponownie.',
      );
    } finally {
      setIsSaving(false);
    }
  };

  const genreOptions: MoviePreferenceOption[] = options.genres.map((label) => ({
    preferenceType: 'genre',
    label,
  }));

  return (
    <section
      aria-labelledby="taste-onboarding-title"
      className="mx-auto flex min-h-[75vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-violet-400/20 bg-ink-900 shadow-card"
    >
      <div className="relative overflow-hidden border-b border-white/[0.08] px-6 py-7 sm:px-8 lg:px-10">
        <div className="absolute -right-16 -top-24 h-64 w-64 rounded-full bg-violet-500/10" aria-hidden="true" />
        <div className="relative flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-violet-400">
              <Sparkles className="h-3.5 w-3.5" />
              Krok obowiązkowy · personalizacja doradcy
            </p>
            <h1 id="taste-onboarding-title" className="text-3xl tracking-[-0.035em] text-white sm:text-4xl">
              Ustaw swoje upodobania filmowe
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              Oznacz, co lubisz i czego wolisz unikać. Dzięki temu pierwsze rekomendacje
              będą dopasowane, nawet zanim porozmawiasz z doradcą.
            </p>
          </div>
          <div className="shrink-0 border-l-2 border-violet-400 px-4 py-2">
            <p className="text-2xl font-semibold text-white">{selectionCount}</p>
            <p className="mt-1 text-[10px] text-slate-600">
              wybrane · minimum 3, w tym lubię i nie lubię
            </p>
          </div>
        </div>
      </div>

      <div className="grid flex-1 gap-8 px-6 py-7 sm:px-8 lg:grid-cols-2 lg:px-10">
        <PreferenceSection
          title="Gatunki"
          description="Wybierz gatunki, po które sięgasz chętnie, oraz te, których nie lubisz."
          icon={<Clapperboard className="h-4 w-4" />}
        >
          {genreOptions.length ? (
            <ChoiceGrid
              options={genreOptions}
              selections={selections}
              onSelect={select}
            />
          ) : (
            <p className="rounded-md border border-dashed border-white/[0.1] p-5 text-xs text-slate-600">
              Gatunki pojawią się po załadowaniu katalogu. Możesz już wybrać cechy filmów.
            </p>
          )}
        </PreferenceSection>

        <PreferenceSection
          title="Klimat i sposób oglądania"
          description="Powiedz doradcy, jakie elementy filmu lub serialu są dla Ciebie ważne."
          icon={<Sparkles className="h-4 w-4" />}
        >
          <ChoiceGrid
            options={options.traits}
            selections={selections}
            onSelect={select}
          />
        </PreferenceSection>
      </div>

      <div className="sticky bottom-0 flex flex-col gap-3 border-t border-white/[0.08] bg-ink-900/95 px-6 py-5 backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
        <div aria-live="polite">
          {saveError ? (
            <p className="text-xs text-red-300" role="alert">{saveError}</p>
          ) : remainingCount > 0 ? (
            <p className="text-xs text-slate-500">
              Wybierz jeszcze {remainingCount} {remainingCount === 1 ? 'pozycję' : 'pozycje'}, aby kontynuować.
            </p>
          ) : likedCount === 0 ? (
            <p className="text-xs text-slate-500">Wybierz przynajmniej jedną rzecz, którą lubisz.</p>
          ) : dislikedCount === 0 ? (
            <p className="text-xs text-slate-500">Wybierz przynajmniej jedną rzecz, której nie lubisz.</p>
          ) : (
            <p className="text-xs text-emerald-300">Gotowe — możesz zapisać swój profil gustu.</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => void save()}
          disabled={!canSave || isSaving}
          className="h-11 rounded-md bg-violet-600 px-6 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-600"
        >
          {isSaving ? 'Zapisywanie…' : 'Zapisz i przejdź do doradcy'}
        </button>
      </div>
    </section>
  );
}

function PreferenceSection({
  title,
  description,
  icon,
  children,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div>
      <div className="mb-4 flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center border border-violet-400/20 bg-violet-500/10 text-violet-300">
          {icon}
        </span>
        <div>
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          <p className="mt-1 text-[10px] leading-4 text-slate-600">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function ChoiceGrid({
  options,
  selections,
  onSelect,
}: {
  options: MoviePreferenceOption[];
  selections: Map<string, MoviePreferenceSelection>;
  onSelect: (preferenceType: string, preferenceValue: string, polarity: -1 | 1) => void;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {options.map((option) => {
        const selection = selections.get(choiceKey(option.preferenceType, option.label));
        return (
          <div
            key={choiceKey(option.preferenceType, option.label)}
            className="flex min-h-12 items-center gap-2 rounded-md border border-white/[0.08] bg-white/[0.02] px-3 py-2"
          >
            <span className="min-w-0 flex-1 text-xs text-slate-300">{option.label}</span>
            <PreferenceButton
              label={`Lubię: ${option.label}`}
              title="Lubię"
              selected={selection?.polarity === 1}
              positive
              onClick={() => onSelect(option.preferenceType, option.label, 1)}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </PreferenceButton>
            <PreferenceButton
              label={`Nie lubię: ${option.label}`}
              title="Nie lubię"
              selected={selection?.polarity === -1}
              onClick={() => onSelect(option.preferenceType, option.label, -1)}
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </PreferenceButton>
          </div>
        );
      })}
    </div>
  );
}

function PreferenceButton({
  label,
  title,
  selected,
  positive = false,
  onClick,
  children,
}: {
  label: string;
  title: string;
  selected: boolean;
  positive?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  const selectedClass = positive
    ? 'border-emerald-400/40 bg-emerald-400/15 text-emerald-200'
    : 'border-red-400/40 bg-red-400/15 text-red-200';
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={selected}
      title={title}
      onClick={onClick}
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition ${
        selected
          ? selectedClass
          : 'border-white/[0.08] text-slate-700 hover:border-white/20 hover:text-slate-300'
      }`}
    >
      {children}
    </button>
  );
}
