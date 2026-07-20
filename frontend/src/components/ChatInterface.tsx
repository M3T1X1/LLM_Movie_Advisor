import { ArrowUp, Bot, CornerDownLeft, Sparkles, UserRound } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { promptSuggestions } from '../data/mockData';
import type { AgentStep, ChatMessage } from '../types';
import { AgentStatus } from './AgentStatus';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  agentSteps: AgentStep[];
  isProcessing: boolean;
  onSubmit: (message: string) => Promise<void>;
}

function formatTime(date: string) {
  return new Intl.DateTimeFormat('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date));
}

export function ChatInterface({
  messages,
  agentSteps,
  isProcessing,
  onSubmit,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentSteps]);

  const sendMessage = async () => {
    const value = input.trim();
    if (!value || isProcessing) return;
    setInput('');
    await onSubmit(value);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    void sendMessage();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  };

  return (
    <section className="flex min-h-[640px] flex-col overflow-hidden rounded-3xl border border-white/[0.08] bg-ink-900/80 shadow-card backdrop-blur-xl lg:sticky lg:top-24 lg:h-[calc(100vh-7.5rem)] lg:min-h-[680px]">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-blue-500/20 text-violet-300 ring-1 ring-violet-400/20">
            <Bot className="h-5 w-5" />
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-ink-900 bg-emerald-400" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-white">Rozmowa z Scene</h2>
            <p className="text-xs text-slate-500">Twój kontekstowy doradca filmowy</p>
          </div>
        </div>
        <span className="rounded-full border border-white/5 bg-white/[0.03] px-2.5 py-1 text-[10px] font-medium text-slate-500">
          Prywatna sesja
        </span>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5 [scrollbar-color:rgba(148,163,184,0.2)_transparent] sm:px-5">
        <div className="flex items-start gap-3">
          <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <div className="rounded-2xl rounded-tl-sm border border-white/5 bg-white/[0.035] px-4 py-3">
            <p className="text-xs leading-relaxed text-slate-400">
              Nie musisz znać tytułu ani gatunku. Opisz nastrój, tempo, motyw lub to, czego chcesz
              uniknąć.
            </p>
          </div>
        </div>

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex items-start gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl ${
                message.role === 'user'
                  ? 'bg-blue-500/15 text-blue-300'
                  : 'bg-violet-500/15 text-violet-300'
              }`}
            >
              {message.role === 'user' ? (
                <UserRound className="h-3.5 w-3.5" />
              ) : (
                <Bot className="h-3.5 w-3.5" />
              )}
            </div>
            <div className={`max-w-[85%] ${message.role === 'user' ? 'text-right' : ''}`}>
              <div
                className={`inline-block rounded-2xl px-4 py-3 text-left ${
                  message.role === 'user'
                    ? 'rounded-tr-sm bg-gradient-to-br from-violet-600 to-blue-600 text-white'
                    : 'rounded-tl-sm border border-white/5 bg-white/[0.04] text-slate-200'
                }`}
              >
                <p className="text-sm leading-relaxed">{message.content}</p>
              </div>
              <p className="mt-1.5 px-1 text-[10px] text-slate-600">{formatTime(message.createdAt)}</p>
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="flex items-center gap-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-violet-500/15 text-violet-300">
              <Bot className="h-3.5 w-3.5" />
            </div>
            <div className="flex gap-1 rounded-2xl rounded-tl-sm border border-white/5 bg-white/[0.04] px-4 py-3">
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  className={`h-1.5 w-1.5 animate-bounce rounded-full bg-violet-300 ${
                    dot === 1 ? '[animation-delay:120ms]' : dot === 2 ? '[animation-delay:240ms]' : ''
                  }`}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {isProcessing && <AgentStatus steps={agentSteps} />}

      <div className="border-t border-white/[0.06] bg-ink-950/50 p-4 sm:p-5">
        {messages.length < 3 && (
          <div className="mb-3 flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
            {promptSuggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={isProcessing}
                onClick={() => setInput(suggestion)}
                className="shrink-0 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-[11px] text-slate-400 transition hover:border-violet-400/30 hover:bg-violet-500/10 hover:text-violet-200 disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-2 transition focus-within:border-violet-400/40 focus-within:bg-white/[0.055] focus-within:ring-4 focus-within:ring-violet-500/5">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
              rows={3}
              maxLength={800}
              placeholder="Na co masz dziś ochotę?"
              className="w-full resize-none bg-transparent px-2 py-1.5 text-sm leading-relaxed text-white outline-none placeholder:text-slate-600 disabled:cursor-wait"
            />
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1.5 text-[10px] text-slate-600">
                <CornerDownLeft className="h-3 w-3" />
                <span>Enter, aby wysłać</span>
              </div>
              <button
                type="submit"
                disabled={!input.trim() || isProcessing}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-ink-950 transition hover:bg-violet-100 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-slate-600"
                aria-label="Wyślij wiadomość"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            </div>
          </div>
        </form>
        <p className="mt-2.5 text-center text-[10px] text-slate-700">
          Rekomendacje AI mogą zawierać błędy. Metadane dostarcza TMDB.
        </p>
      </div>
    </section>
  );
}
