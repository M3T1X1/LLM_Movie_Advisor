import { createContext, type ReactNode, useContext, useEffect, useState } from 'react';
import {
  demoConversations,
  demoInteractions,
  demoPreferences,
  demoProfile,
  demoUser,
  initialMessages,
} from '../data/mockData';
import type {
  AppUser,
  ChatMessage,
  Conversation,
  DatabaseId,
  Interaction,
  InteractionType,
  MessageRole,
  UserPreference,
  UserSemanticProfile,
} from '../types';

interface StoredSession {
  user: AppUser;
  semanticProfile: UserSemanticProfile;
  preferences: UserPreference[];
  conversations: Conversation[];
  currentConversationId: DatabaseId | null;
  messages: ChatMessage[];
  interactions: Interaction[];
}

interface PreferenceGroups {
  favoriteGenres: string[];
  positivePreferences: string[];
  avoidedPreferences: string[];
}

interface SessionContextValue extends StoredSession {
  watchlistedContentIds: DatabaseId[];
  watchedContentIds: DatabaseId[];
  createConversation: () => Conversation;
  selectConversation: (conversationId: DatabaseId) => void;
  renameConversation: (conversationId: DatabaseId, title: string) => void;
  deleteConversation: (conversationId: DatabaseId) => void;
  addMessage: (role: MessageRole, content: string) => ChatMessage;
  appendMessage: (message: ChatMessage) => void;
  updateUser: (changes: Partial<Pick<AppUser, 'username' | 'email'>>) => void;
  replacePreferenceGroups: (groups: PreferenceGroups) => void;
  addDetectedPreferences: (preferences: UserPreference[]) => void;
  updateConversationFromQuery: (query: string) => void;
  recordInteraction: (
    contentId: DatabaseId,
    sourceCandidateId: DatabaseId | null,
    interactionType: InteractionType,
    rating?: number,
  ) => void;
  removeInteraction: (
    contentId: DatabaseId,
    interactionType: 'watchlisted' | 'watched',
  ) => Interaction | null;
}

const STORAGE_KEY = 'scene-ai-session-erd-v2';
const SessionContext = createContext<SessionContextValue | undefined>(undefined);
let localIdOffset = 0;

function createLocalDatabaseId() {
  localIdOffset += 1;
  return String(Date.now() + localIdOffset);
}

function createInitialSession(): StoredSession {
  return {
    user: demoUser,
    semanticProfile: demoProfile,
    preferences: demoPreferences,
    conversations: demoConversations,
    currentConversationId: demoConversations[0]?.id ?? null,
    messages: initialMessages,
    interactions: demoInteractions,
  };
}

function loadSession(): StoredSession {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return createInitialSession();

    const parsed = JSON.parse(stored) as Omit<StoredSession, 'currentConversationId'> & {
      currentConversationId?: DatabaseId | null;
    };
    const currentConversationId = parsed.conversations.some(
      (conversation) => conversation.id === parsed.currentConversationId,
    )
      ? (parsed.currentConversationId ?? null)
      : (parsed.conversations[0]?.id ?? null);

    return { ...parsed, currentConversationId };
  } catch {
    return createInitialSession();
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession>(loadSession);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }, [session]);

  const createConversation = () => {
    const timestamp = new Date().toISOString();
    const conversation: Conversation = {
      id: createLocalDatabaseId(),
      userId: session.user.id,
      title: null,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    setSession((current) => ({
      ...current,
      conversations: [conversation, ...current.conversations],
      currentConversationId: conversation.id,
    }));
    return conversation;
  };

  const selectConversation = (conversationId: DatabaseId) => {
    setSession((current) =>
      current.conversations.some((conversation) => conversation.id === conversationId)
        ? { ...current, currentConversationId: conversationId }
        : current,
    );
  };

  const renameConversation = (conversationId: DatabaseId, title: string) => {
    const normalizedTitle = title.trim().slice(0, 255);
    if (!normalizedTitle) return;

    setSession((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, title: normalizedTitle, updatedAt: new Date().toISOString() }
          : conversation,
      ),
    }));
  };

  const deleteConversation = (conversationId: DatabaseId) => {
    setSession((current) => {
      const conversations = current.conversations.filter(
        (conversation) => conversation.id !== conversationId,
      );
      return {
        ...current,
        conversations,
        currentConversationId:
          current.currentConversationId === conversationId
            ? (conversations[0]?.id ?? null)
            : current.currentConversationId,
        messages: current.messages.filter(
          (message) => message.conversationId !== conversationId,
        ),
      };
    });
  };

  const addMessage = (role: MessageRole, content: string) => {
    if (!session.currentConversationId) {
      throw new Error('Nie wybrano aktywnej rozmowy.');
    }
    const conversationId = session.currentConversationId;
    const conversationMessages = session.messages.filter(
      (message) => message.conversationId === conversationId,
    );
    const sequenceNo = Math.max(0, ...conversationMessages.map((message) => message.sequenceNo)) + 1;
    const message: ChatMessage = {
      id: createLocalDatabaseId(),
      conversationId,
      role,
      content,
      sequenceNo,
      createdAt: new Date().toISOString(),
    };
    setSession((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, updatedAt: message.createdAt }
          : conversation,
      ),
      messages: [...current.messages, message],
    }));
    return message;
  };

  const appendMessage = (message: ChatMessage) => {
    setSession((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === message.conversationId
          ? { ...conversation, updatedAt: message.createdAt }
          : conversation,
      ),
      messages: current.messages.some((item) => item.id === message.id)
        ? current.messages
        : [...current.messages, message],
    }));
  };

  const updateUser = (changes: Partial<Pick<AppUser, 'username' | 'email'>>) => {
    setSession((current) => ({
      ...current,
      user: { ...current.user, ...changes },
    }));
  };

  const replacePreferenceGroups = (groups: PreferenceGroups) => {
    const favoriteGenres = Array.from(new Set(groups.favoriteGenres));
    const positivePreferences = Array.from(new Set(groups.positivePreferences));
    const positiveValues = new Set(positivePreferences);
    const avoidedPreferences = Array.from(new Set(groups.avoidedPreferences)).filter(
      (value) => !positiveValues.has(value),
    );

    setSession((current) => {
      const timestamp = new Date().toISOString();
      const mapPreference = (
        preferenceValue: string,
        polarity: -1 | 1,
        requiredType?: string,
      ): UserPreference => {
        const existing = current.preferences.find(
          (preference) =>
            preference.preferenceValue === preferenceValue &&
            (requiredType
              ? preference.preferenceType === requiredType
              : preference.preferenceType !== 'genre'),
        );
        return existing
          ? { ...existing, polarity, updatedAt: timestamp }
          : {
              id: createLocalDatabaseId(),
              userId: current.user.id,
              preferenceType: requiredType ?? 'user_defined',
              preferenceValue,
              polarity,
              weight: 1,
              confidence: 1,
              createdAt: timestamp,
              updatedAt: timestamp,
            };
      };

      const preferences = [
        ...favoriteGenres.map((value) => mapPreference(value, 1, 'genre')),
        ...positivePreferences.map((value) => mapPreference(value, 1)),
        ...avoidedPreferences.map((value) => mapPreference(value, -1)),
      ];
      return { ...current, preferences };
    });
  };

  const addDetectedPreferences = (detectedPreferences: UserPreference[]) => {
    setSession((current) => {
      const merged = [...current.preferences];
      detectedPreferences.forEach((preference) => {
        const index = merged.findIndex(
          (item) =>
            item.preferenceType === preference.preferenceType &&
            item.preferenceValue === preference.preferenceValue,
        );
        if (index >= 0) merged[index] = preference;
        else merged.push(preference);
      });
      return { ...current, preferences: merged };
    });
  };

  const updateConversationFromQuery = (query: string) => {
    setSession((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === current.currentConversationId
          ? {
              ...conversation,
              title: conversation.title ?? query.slice(0, 255),
              updatedAt: new Date().toISOString(),
            }
          : conversation,
      ),
    }));
  };

  const recordInteraction = (
    contentId: DatabaseId,
    sourceCandidateId: DatabaseId | null,
    interactionType: InteractionType,
    rating?: number,
  ) => {
    setSession((current) => {
      if (
        interactionType === 'rated' &&
        (rating === undefined || rating < 0 || rating > 10)
      ) {
        return current;
      }
      const isSingleStateEvent = interactionType === 'watchlisted' || interactionType === 'watched';
      const alreadyRecorded = current.interactions.some(
        (interaction) =>
          interaction.contentId === contentId && interaction.interactionType === interactionType,
      );
      if (isSingleStateEvent && alreadyRecorded) return current;

      const interaction: Interaction = {
        id: createLocalDatabaseId(),
        userId: current.user.id,
        contentId,
        sourceCandidateId,
        interactionType,
        rating: interactionType === 'rated' ? (rating ?? null) : null,
        metadata: {},
        createdAt: new Date().toISOString(),
      };
      return { ...current, interactions: [...current.interactions, interaction] };
    });
  };

  const removeInteraction = (
    contentId: DatabaseId,
    interactionType: 'watchlisted' | 'watched',
  ) => {
    const interaction = [...session.interactions]
      .reverse()
      .find(
        (item) => item.contentId === contentId && item.interactionType === interactionType,
      );
    if (!interaction) return null;

    setSession((current) => ({
      ...current,
      interactions: current.interactions.filter((item) => item.id !== interaction.id),
    }));
    return interaction;
  };

  const watchlistedContentIds = Array.from(
    new Set(
      session.interactions
        .filter((interaction) => interaction.interactionType === 'watchlisted')
        .map((interaction) => interaction.contentId),
    ),
  );
  const watchedContentIds = Array.from(
    new Set(
      session.interactions
        .filter((interaction) => interaction.interactionType === 'watched')
        .map((interaction) => interaction.contentId),
    ),
  );

  const value: SessionContextValue = {
    ...session,
    watchlistedContentIds,
    watchedContentIds,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    addMessage,
    appendMessage,
    updateUser,
    replacePreferenceGroups,
    addDetectedPreferences,
    updateConversationFromQuery,
    recordInteraction,
    removeInteraction,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error('useSession musi być użyty wewnątrz SessionProvider.');
  return context;
}
