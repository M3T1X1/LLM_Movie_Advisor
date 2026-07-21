import {
  Bookmark,
  Check,
  Clock3,
  Eye,
  MessageSquareText,
  Pencil,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
  X,
} from 'lucide-react';
import { useState, type FormEvent, type ReactNode } from 'react';
import type {
  AppUser,
  Conversation,
  UserPreference,
  UserSemanticProfile,
} from '../types';

interface ProfileViewProps {
  user: AppUser;
  semanticProfile: UserSemanticProfile;
  preferences: UserPreference[];
  conversations: Conversation[];
  savedCount: number;
  watchedCount: number;
  onUpdateUser: (changes: Partial<Pick<AppUser, 'username' | 'email'>>) => void;
}

interface ProfileFormState {
  username: string;
  email: string;
}

function createFormState(user: AppUser): ProfileFormState {
  return {
    username: user.username,
    email: user.email,
  };
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function ProfileView({
  user,
  semanticProfile,
  preferences,
  conversations,
  savedCount,
  watchedCount,
  onUpdateUser,
}: ProfileViewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState<ProfileFormState>(() => createFormState(user));
  const initials = user.username.slice(0, 2).toUpperCase();
  const favoriteGenres = preferences
    .filter((preference) => preference.preferenceType === 'genre' && preference.polarity === 1)
    .map((preference) => preference.preferenceValue);
  const positivePreferences = preferences
    .filter((preference) => preference.preferenceType !== 'genre' && preference.polarity === 1)
    .map((preference) => preference.preferenceValue);
  const avoidedPreferences = preferences
    .filter((preference) => preference.polarity === -1)
    .map((preference) => preference.preferenceValue);

  const startEditing = () => {
    setForm(createFormState(user));
    setIsEditing(true);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onUpdateUser({
      username: form.username.trim() || user.username,
      email: form.email.trim() || user.email,
    });
    setIsEditing(false);
  };

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-7">
        <p className="mb-2 flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-600">
          Konto użytkownika
        </p>
        <div className="flex flex-col justify-between gap-5 border-b border-white/[0.07] pb-7 sm:flex-row sm:items-end">
          <div className="flex items-center gap-4">
            <span className="flex h-16 w-16 items-center justify-center rounded-xl bg-slate-800 text-lg font-semibold text-white">
              {initials}
            </span>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">{user.username}</h1>
              <p className="mt-1 text-sm text-slate-500">{user.email}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={startEditing}
            className="flex h-9 w-fit items-center gap-2 rounded-md border border-white/[0.1] px-3 text-xs font-medium text-slate-300 transition hover:border-white/20 hover:bg-white/[0.04] hover:text-white"
          >
            <Pencil className="h-3.5 w-3.5" />
            Edytuj profil
          </button>
        </div>
      </div>

      <div className="mb-7 grid grid-cols-3 overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15]">
        <ProfileStat icon={<Bookmark className="h-4 w-4" />} value={savedCount} label="Zapisane" />
        <ProfileStat icon={<Eye className="h-4 w-4" />} value={watchedCount} label="Obejrzane" bordered />
        <ProfileStat
          icon={<MessageSquareText className="h-4 w-4" />}
          value={conversations.length}
          label="Rozmowy"
        />
      </div>

      {isEditing ? (
        <form onSubmit={handleSubmit} className="rounded-xl border border-white/[0.1] bg-[#0d0f15] p-5 sm:p-6">
          <div className="mb-6 flex items-center justify-between border-b border-white/[0.06] pb-4">
            <div>
              <h2 className="text-sm font-semibold text-white">Edycja profilu</h2>
              <p className="mt-1 text-[11px] text-slate-600">
                Gusta są aktualizowane automatycznie na podstawie Twojej aktywności.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="text-slate-600 transition hover:text-white"
              aria-label="Anuluj edycję"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <ProfileInput
              label="Nazwa użytkownika"
              value={form.username}
              onChange={(value) => setForm((current) => ({ ...current, username: value }))}
            />
            <ProfileInput
              label="Adres e-mail"
              type="email"
              value={form.email}
              onChange={(value) => setForm((current) => ({ ...current, email: value }))}
            />
          </div>

          <div className="mt-6 flex justify-end gap-2 border-t border-white/[0.06] pt-4">
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="h-9 rounded-md px-3 text-xs text-slate-500 transition hover:text-white"
            >
              Anuluj
            </button>
            <button
              type="submit"
              className="flex h-9 items-center gap-2 rounded-md bg-violet-600 px-3 text-xs font-medium text-white transition hover:bg-violet-500"
            >
              <Check className="h-3.5 w-3.5" />
              Zapisz zmiany
            </button>
          </div>
        </form>
      ) : (
        <div className="grid gap-7 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
          <div className="space-y-5">
            <ProfileSection title="Twój gust" icon={<SlidersHorizontal className="h-4 w-4" />}>
              <PreferenceGroup label="Ulubione gatunki" values={favoriteGenres} />
              <PreferenceGroup label="Zapamiętane preferencje" values={positivePreferences} />
              <PreferenceGroup label="Pomijaj w rekomendacjach" values={avoidedPreferences} muted />
              {semanticProfile.semanticSummary && (
                <div className="mt-5 border-t border-white/[0.06] pt-4">
                  <p className="mb-2 text-[10px] text-slate-600">Podsumowanie semantyczne</p>
                  <p className="text-xs leading-5 text-slate-500">{semanticProfile.semanticSummary}</p>
                </div>
              )}
            </ProfileSection>

            <ProfileSection title="Ostatnia aktywność" icon={<Clock3 className="h-4 w-4" />}>
              {conversations.length ? (
                <div className="divide-y divide-white/[0.05]">
                  {conversations.slice(0, 4).map((conversation) => (
                    <div key={conversation.id} className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
                      <div className="min-w-0">
                        <p className="truncate text-xs text-slate-300">
                          {conversation.title ?? 'Rozmowa bez tytułu'}
                        </p>
                      </div>
                      <time className="shrink-0 text-[10px] text-slate-600">
                        {formatDate(conversation.updatedAt)}
                      </time>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-600">Brak zapisanych rozmów.</p>
              )}
            </ProfileSection>
          </div>

          <div className="space-y-5">
            <ProfileSection title="Konto" icon={<UserRound className="h-4 w-4" />}>
              <dl className="space-y-4 text-xs">
                <div>
                  <dt className="text-[10px] text-slate-600">Nazwa użytkownika</dt>
                  <dd className="mt-1 text-slate-300">{user.username}</dd>
                </div>
                <div>
                  <dt className="text-[10px] text-slate-600">Adres e-mail</dt>
                  <dd className="mt-1 break-all text-slate-300">{user.email}</dd>
                </div>
              </dl>
            </ProfileSection>

            <ProfileSection title="Prywatność" icon={<ShieldCheck className="h-4 w-4" />}>
              <p className="text-xs leading-5 text-slate-500">
                Historia rozmów i profil gustu są przypisane wyłącznie do Twojego konta.
              </p>
              <div className="mt-4 flex items-center gap-2 text-[10px] text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Profil prywatny
              </div>
            </ProfileSection>
          </div>
        </div>
      )}
    </div>
  );
}

function ProfileStat({
  icon,
  value,
  label,
  bordered = false,
}: {
  icon: ReactNode;
  value: number;
  label: string;
  bordered?: boolean;
}) {
  return (
    <div className={`p-4 sm:p-5 ${bordered ? 'border-x border-white/[0.06]' : ''}`}>
      <div className="mb-3 text-slate-600">{icon}</div>
      <p className="text-xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-[10px] text-slate-600">{label}</p>
    </div>
  );
}

function ProfileSection({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-white/[0.08] bg-[#0d0f15] p-5">
      <div className="mb-5 flex items-center gap-2 border-b border-white/[0.06] pb-3 text-slate-500">
        {icon}
        <h2 className="text-xs font-semibold text-slate-300">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function PreferenceGroup({ label, values, muted = false }: { label: string; values: string[]; muted?: boolean }) {
  return (
    <div className="mb-5 last:mb-0">
      <p className="mb-2 text-[10px] text-slate-600">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {values.length ? (
          values.map((value) => (
            <span
              key={value}
              className={`rounded border px-2 py-1 text-[10px] ${
                muted
                  ? 'border-red-400/10 bg-red-400/[0.04] text-slate-500'
                  : 'border-white/[0.08] bg-white/[0.025] text-slate-400'
              }`}
            >
              {value}
            </span>
          ))
        ) : (
          <span className="text-[10px] text-slate-700">Brak danych</span>
        )}
      </div>
    </div>
  );
}

function ProfileInput({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-[10px] font-medium text-slate-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-md border border-white/[0.08] bg-white/[0.025] px-3 text-xs text-white outline-none transition placeholder:text-slate-700 focus:border-violet-500/60"
      />
    </label>
  );
}
