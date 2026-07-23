import { ArrowUp, Bot, CornerDownLeft } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import type { AgentStep, ChatMessage } from '../types';

const promptSuggestions = [
  'Coś mrocznego z twistem, bez happy endu',
  'Lekki serial na dwa wieczory',
  'Ambitne sci-fi, które daje do myślenia',
];
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
    <section className="flex min-h-[680px] flex-col overflow-hidden rounded-xl border border-white/[0.1] bg-[#0d0f15] xl:sticky xl:top-[76px] xl:h-[calc(100vh-6rem)] xl:min-h-[700px]">
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4 sm:px-6">
        <span className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 text-white">
          <Bot className="h-4 w-4" />
          <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-[#0d0f15] bg-emerald-400" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-white">Chat</h2>
          <p className="mt-0.5 text-[10px] text-slate-600">FilmiQ</p>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-5 py-6 [scrollbar-color:rgba(148,163,184,0.16)_transparent] sm:px-6">
        {messages.length === 0 && !isProcessing && (
          <div className="flex min-h-64 flex-col items-center justify-center text-center">
            <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-violet-500/10 text-violet-300">
              <Bot className="h-5 w-5" />
            </span>
            <h3 className="text-sm font-semibold text-slate-200">Nowa rozmowa</h3>
            <p className="mt-2 max-w-xs text-xs leading-5 text-slate-600">
              Opisz, czego chcesz dziś poszukać. Rekomendacje pojawią się dopiero po wysłaniu
              Twojej wiadomości.
            </p>
          </div>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={message.role === 'user' ? 'ml-auto max-w-[82%]' : 'max-w-[82%]'}
          >
            <div className="mb-1.5 flex items-center gap-2">
              <span className="text-[10px] font-medium text-slate-500">
                {message.role === 'user' ? 'Ty' : 'FilmiQ'}
              </span>
              <span className="text-[9px] text-slate-700">{formatTime(message.createdAt)}</span>
            </div>
            <div
              className={`rounded-lg px-3.5 py-3 text-sm leading-6 ${
                message.role === 'user'
                  ? 'bg-violet-600 text-white'
                  : 'border border-white/[0.06] bg-white/[0.025] text-slate-300'
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}

        {isProcessing && (
          <div className="max-w-[82%]">
            <p className="mb-1.5 text-[10px] font-medium text-slate-500">Scene</p>
            <div className="flex w-fit gap-1 rounded-lg border border-white/[0.06] bg-white/[0.025] px-3.5 py-3.5">
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  className={`h-1 w-1 animate-bounce rounded-full bg-slate-400 ${
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

      <div className="border-t border-white/[0.06] p-4 sm:p-5">
        {messages.length < 3 && (
          <div className="mb-3 flex gap-2 overflow-x-auto [scrollbar-width:none]">
            {promptSuggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={isProcessing}
                onClick={() => setInput(suggestion)}
                className="shrink-0 rounded-md border border-white/[0.08] px-2.5 py-1.5 text-[10px] text-slate-500 transition hover:border-white/15 hover:text-slate-300 disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="rounded-lg border border-white/10 bg-[#12151d] p-2 transition focus-within:border-violet-500/60">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
              rows={4}
              maxLength={800}
              placeholder="Opisz nastrój, tempo albo motyw..."
              className="w-full resize-none bg-transparent px-1.5 py-1 text-sm leading-6 text-white outline-none placeholder:text-slate-700 disabled:cursor-wait"
            />
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-1.5 text-[9px] text-slate-700">
                <CornerDownLeft className="h-3 w-3" />
                Enter, aby wysłać
              </div>
              <button
                type="submit"
                disabled={!input.trim() || isProcessing}
                className="flex h-8 w-8 items-center justify-center rounded-md bg-violet-600 text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-600"
                aria-label="Wyślij wiadomość"
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </form>
        <p className="mt-2 text-center text-[9px] text-slate-700">Metadane filmowe pochodzą z TMDB</p>
      </div>
    </section>
  );
}
