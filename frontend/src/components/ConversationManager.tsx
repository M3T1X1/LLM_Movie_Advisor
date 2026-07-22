import { Check, MessageSquareText, Pencil, Plus, Trash2, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import type { Conversation, DatabaseId } from '../types';

interface ConversationManagerProps {
  conversations: Conversation[];
  currentConversationId: DatabaseId | null;
  disabled?: boolean;
  onCreate: () => void;
  onSelect: (conversationId: DatabaseId) => void;
  onRename: (conversationId: DatabaseId, title: string) => void;
  onDelete: (conversationId: DatabaseId) => void;
}

function formatConversationDate(date: string) {
  return new Intl.DateTimeFormat('pl-PL', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function ConversationManager({
  conversations,
  currentConversationId,
  disabled = false,
  onCreate,
  onSelect,
  onRename,
  onDelete,
}: ConversationManagerProps) {
  const [renamedConversationId, setRenamedConversationId] = useState<DatabaseId | null>(null);
  const [title, setTitle] = useState('');
  const [deletedConversationId, setDeletedConversationId] = useState<DatabaseId | null>(null);
  const orderedConversations = [...conversations].sort(
    (first, second) =>
      new Date(second.updatedAt).getTime() - new Date(first.updatedAt).getTime(),
  );

  const startRenaming = (conversation: Conversation) => {
    setDeletedConversationId(null);
    setRenamedConversationId(conversation.id);
    setTitle(conversation.title ?? '');
  };

  const cancelRenaming = () => {
    setRenamedConversationId(null);
    setTitle('');
  };

  const submitRename = (event: FormEvent) => {
    event.preventDefault();
    if (!renamedConversationId || !title.trim()) return;
    onRename(renamedConversationId, title);
    cancelRenaming();
  };

  const confirmDelete = (conversationId: DatabaseId) => {
    onDelete(conversationId);
    setDeletedConversationId(null);
    if (renamedConversationId === conversationId) cancelRenaming();
  };

  return (
    <aside className="flex min-h-[680px] flex-col overflow-hidden rounded-xl border border-white/[0.08] bg-[#0d0f15] xl:sticky xl:top-[76px] xl:h-[calc(100vh-6rem)] xl:min-h-[700px]">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-4">
        <div>
          <h2 className="text-xs font-semibold text-white">Historia Rozmów</h2>
          <p className="mt-1 text-[9px] text-slate-600">{conversations.length} zapisanych</p>
        </div>
        <button
          type="button"
          onClick={onCreate}
          disabled={disabled}
          className="flex h-8 items-center gap-1.5 rounded-md bg-violet-600 px-2.5 text-[10px] font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Nowa rozmowa"
        >
          <Plus className="h-3.5 w-3.5" />
          Nowa
        </button>
      </div>

      {orderedConversations.length ? (
        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2 [scrollbar-color:rgba(148,163,184,0.16)_transparent]">
          {orderedConversations.map((conversation) => {
            const isActive = conversation.id === currentConversationId;
            const isRenaming = conversation.id === renamedConversationId;
            const isDeleting = conversation.id === deletedConversationId;

            if (isRenaming) {
              return (
                <form
                  key={conversation.id}
                  onSubmit={submitRename}
                  className="rounded-lg border border-violet-400/30 bg-violet-500/[0.06] p-2"
                >
                  <label className="block">
                    <span className="sr-only">Nazwa rozmowy</span>
                    <input
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      maxLength={255}
                      autoFocus
                      className="h-8 w-full rounded border border-white/[0.1] bg-black/20 px-2 text-[11px] text-white outline-none focus:border-violet-400/60"
                      aria-label="Nazwa rozmowy"
                    />
                  </label>
                  <div className="mt-2 flex justify-end gap-1">
                    <button
                      type="button"
                      onClick={cancelRenaming}
                      className="flex h-7 w-7 items-center justify-center rounded text-slate-500 transition hover:bg-white/[0.06] hover:text-white"
                      aria-label="Anuluj zmianę nazwy"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="submit"
                      disabled={!title.trim()}
                      className="flex h-7 w-7 items-center justify-center rounded bg-violet-600 text-white transition hover:bg-violet-500 disabled:opacity-40"
                      aria-label="Zapisz nazwę rozmowy"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </form>
              );
            }

            return (
              <div
                key={conversation.id}
                className={`rounded-lg border transition ${
                  isActive
                    ? 'border-violet-400/25 bg-violet-500/[0.08]'
                    : 'border-transparent hover:border-white/[0.06] hover:bg-white/[0.025]'
                }`}
              >
                <div className="flex items-start gap-1 p-1.5">
                  <button
                    type="button"
                    onClick={() => onSelect(conversation.id)}
                    disabled={disabled}
                    className="min-w-0 flex-1 rounded px-1.5 py-1.5 text-left disabled:cursor-not-allowed disabled:opacity-50"
                    aria-current={isActive ? 'true' : undefined}
                  >
                    <span className="block truncate text-[11px] font-medium text-slate-300">
                      {conversation.title ?? 'Nowa rozmowa'}
                    </span>
                    <time className="mt-1 block text-[9px] text-slate-700">
                      {formatConversationDate(conversation.updatedAt)}
                    </time>
                  </button>
                  <button
                    type="button"
                    onClick={() => startRenaming(conversation)}
                    disabled={disabled}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-slate-700 transition hover:bg-white/[0.06] hover:text-slate-300 disabled:cursor-not-allowed disabled:opacity-40"
                    aria-label={`Zmień nazwę rozmowy: ${conversation.title ?? 'Nowa rozmowa'}`}
                  >
                    <Pencil className="h-3 w-3" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setRenamedConversationId(null);
                      setDeletedConversationId(conversation.id);
                    }}
                    disabled={disabled}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-slate-700 transition hover:bg-red-500/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-40"
                    aria-label={`Usuń rozmowę: ${conversation.title ?? 'Nowa rozmowa'}`}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>

                {isDeleting && (
                  <div className="border-t border-white/[0.06] px-2.5 py-2">
                    <p className="text-[10px] leading-4 text-slate-500">Usunąć rozmowę i jej wiadomości?</p>
                    <div className="mt-2 flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setDeletedConversationId(null)}
                        className="text-[10px] text-slate-500 transition hover:text-white"
                      >
                        Anuluj
                      </button>
                      <button
                        type="button"
                        onClick={() => confirmDelete(conversation.id)}
                        className="rounded bg-red-500/15 px-2 py-1 text-[10px] font-medium text-red-300 transition hover:bg-red-500/25"
                      >
                        Usuń
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-5 py-8 text-center">
          <MessageSquareText className="mb-3 h-5 w-5 text-slate-700" />
          <p className="text-xs font-medium text-slate-400">Brak rozmów</p>
          <p className="mt-1 text-[10px] leading-4 text-slate-600">
            Rozpocznij rozmowę, aby wysłać pierwszy prompt.
          </p>
        </div>
      )}
    </aside>
  );
}
