import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from 'react';
import { demoHistory, demoUser, initialMessages } from '../data/mockData';
import type {
  ChatMessage,
  MessageRole,
  RecommendationHistoryItem,
  UserProfile,
} from '../types';

interface StoredSession {
  user: UserProfile;
  savedMovieIds: number[];
  watchedMovieIds: number[];
  history: RecommendationHistoryItem[];
}

interface SessionContextValue extends StoredSession {
  messages: ChatMessage[];
  addMessage: (role: MessageRole, content: string) => void;
  toggleSaved: (movieId: number) => void;
  toggleWatched: (movieId: number) => void;
  addDetectedPreferences: (preferences: string[]) => void;
  recordInteraction: (query: string, resultCount: number) => void;
}

const STORAGE_KEY = 'scene-ai-session';
const SessionContext = createContext<SessionContextValue | undefined>(undefined);

function loadSession(): StoredSession {
  const fallback: StoredSession = {
    user: demoUser,
    savedMovieIds: [210577],
    watchedMovieIds: [],
    history: demoHistory,
  };

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored ? { ...fallback, ...JSON.parse(stored) } : fallback;
  } catch {
    return fallback;
  }
}

function createMessage(role: MessageRole, content: string): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    createdAt: new Date().toISOString(),
  };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [storedSession, setStoredSession] = useState<StoredSession>(loadSession);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(storedSession));
  }, [storedSession]);

  const addMessage = (role: MessageRole, content: string) => {
    setMessages((current) => [...current, createMessage(role, content)]);
  };

  const toggleSaved = (movieId: number) => {
    setStoredSession((current) => ({
      ...current,
      savedMovieIds: current.savedMovieIds.includes(movieId)
        ? current.savedMovieIds.filter((id) => id !== movieId)
        : [...current.savedMovieIds, movieId],
    }));
  };

  const toggleWatched = (movieId: number) => {
    setStoredSession((current) => ({
      ...current,
      watchedMovieIds: current.watchedMovieIds.includes(movieId)
        ? current.watchedMovieIds.filter((id) => id !== movieId)
        : [...current.watchedMovieIds, movieId],
    }));
  };

  const addDetectedPreferences = (preferences: string[]) => {
    setStoredSession((current) => ({
      ...current,
      user: {
        ...current.user,
        preferences: Array.from(new Set([...preferences, ...current.user.preferences])).slice(0, 6),
      },
    }));
  };

  const recordInteraction = (query: string, resultCount: number) => {
    const item: RecommendationHistoryItem = {
      id: crypto.randomUUID(),
      query,
      resultCount,
      createdAt: new Date().toISOString(),
    };

    setStoredSession((current) => ({
      ...current,
      history: [item, ...current.history].slice(0, 12),
    }));
  };

  const value: SessionContextValue = {
    ...storedSession,
    messages,
    addMessage,
    toggleSaved,
    toggleWatched,
    addDetectedPreferences,
    recordInteraction,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);

  if (!context) {
    throw new Error('useSession musi być użyty wewnątrz SessionProvider.');
  }

  return context;
}
