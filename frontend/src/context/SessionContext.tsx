import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import {
  createConversation as createConversationRequest,
  createInteraction as createInteractionRequest,
  createMessage,
  deleteConversation as deleteConversationRequest,
  deleteInteraction as deleteInteractionRequest,
  getAuthSession,
  getBootstrap,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  renameConversation as renameConversationRequest,
  updateProfile,
} from '../services/api';
import type {
  AppBootstrap,
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

interface SessionState {
  user: AppUser | null;
  semanticProfile: UserSemanticProfile | null;
  preferences: UserPreference[];
  conversations: Conversation[];
  currentConversationId: DatabaseId | null;
  messages: ChatMessage[];
  interactions: Interaction[];
}

interface SessionContextValue extends SessionState {
  isLoading: boolean;
  isAuthenticated: boolean;
  watchlistedContentIds: DatabaseId[];
  watchedContentIds: DatabaseId[];
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  createConversation: () => Promise<Conversation>;
  selectConversation: (conversationId: DatabaseId) => void;
  renameConversation: (conversationId: DatabaseId, title: string) => Promise<void>;
  deleteConversation: (conversationId: DatabaseId) => Promise<void>;
  addMessage: (role: MessageRole, content: string) => Promise<ChatMessage>;
  updateUser: (
    changes: Partial<Pick<AppUser, 'username' | 'email'>>,
  ) => Promise<void>;
  recordInteraction: (
    contentId: DatabaseId,
    sourceCandidateId: DatabaseId | null,
    interactionType: InteractionType,
    rating?: number,
  ) => Promise<Interaction | null>;
  removeInteraction: (
    contentId: DatabaseId,
    interactionType: 'watchlisted' | 'watched',
  ) => Promise<void>;
}

const emptySession: SessionState = {
  user: null,
  semanticProfile: null,
  preferences: [],
  conversations: [],
  currentConversationId: null,
  messages: [],
  interactions: [],
};

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

function stateFromBootstrap(data: AppBootstrap): SessionState {
  return {
    ...data,
    currentConversationId: data.conversations[0]?.id ?? null,
  };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionState>(emptySession);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCurrent = true;
    void getAuthSession()
      .then(async (authSession) => {
        if (!authSession.authenticated) return null;
        return getBootstrap();
      })
      .then((bootstrap) => {
        if (!isCurrent || !bootstrap) return;
        setSession(stateFromBootstrap(bootstrap));
      })
      .catch(() => {
        if (isCurrent) setSession(emptySession);
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const loadAuthenticatedSession = async () => {
    const bootstrap = await getBootstrap();
    setSession(stateFromBootstrap(bootstrap));
  };

  const login = async (email: string, password: string) => {
    await loginRequest(email, password);
    await loadAuthenticatedSession();
  };

  const register = async (username: string, email: string, password: string) => {
    await registerRequest(username, email, password);
    await loadAuthenticatedSession();
  };

  const logout = async () => {
    await logoutRequest();
    setSession(emptySession);
  };

  const createConversation = async () => {
    const conversation = await createConversationRequest();
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

  const renameConversation = async (conversationId: DatabaseId, title: string) => {
    const conversation = await renameConversationRequest(conversationId, title);
    setSession((current) => ({
      ...current,
      conversations: current.conversations.map((item) =>
        item.id === conversationId ? conversation : item,
      ),
    }));
  };

  const deleteConversation = async (conversationId: DatabaseId) => {
    await deleteConversationRequest(conversationId);
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

  const addMessage = async (role: MessageRole, content: string) => {
    if (role !== 'user') {
      throw new Error('Backend przyjmuje obecnie wyłącznie wiadomości użytkownika.');
    }
    const conversationId = session.currentConversationId;
    if (!conversationId) throw new Error('Nie wybrano aktywnej rozmowy.');
    const message = await createMessage(conversationId, content);
    setSession((current) => ({
      ...current,
      messages: [...current.messages, message],
      conversations: current.conversations.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              title: conversation.title ?? content.slice(0, 255),
              updatedAt: message.createdAt,
            }
          : conversation,
      ),
    }));
    return message;
  };

  const updateUser = async (
    changes: Partial<Pick<AppUser, 'username' | 'email'>>,
  ) => {
    if (!session.user) throw new Error('Brak aktywnego użytkownika.');
    const user = await updateProfile({
      username: changes.username ?? session.user.username,
      email: changes.email ?? session.user.email,
    });
    setSession((current) => ({ ...current, user }));
  };

  const recordInteraction = async (
    contentId: DatabaseId,
    sourceCandidateId: DatabaseId | null,
    interactionType: InteractionType,
    rating?: number,
  ) => {
    if (
      interactionType === 'rated' &&
      (rating === undefined || rating < 0 || rating > 10)
    ) {
      return null;
    }
    const singleState = interactionType === 'watchlisted' || interactionType === 'watched';
    const existing = session.interactions.find(
      (interaction) =>
        interaction.contentId === contentId &&
        interaction.interactionType === interactionType,
    );
    if (singleState && existing) return existing;
    const interaction = await createInteractionRequest(
      contentId,
      sourceCandidateId,
      interactionType,
      rating ?? null,
    );
    setSession((current) => ({
      ...current,
      interactions: current.interactions.some((item) => item.id === interaction.id)
        ? current.interactions
        : [...current.interactions, interaction],
    }));
    return interaction;
  };

  const removeInteraction = async (
    contentId: DatabaseId,
    interactionType: 'watchlisted' | 'watched',
  ) => {
    const interaction = [...session.interactions]
      .reverse()
      .find(
        (item) =>
          item.contentId === contentId && item.interactionType === interactionType,
      );
    if (!interaction) return;
    await deleteInteractionRequest(interaction.id);
    setSession((current) => ({
      ...current,
      interactions: current.interactions.filter((item) => item.id !== interaction.id),
    }));
  };

  const watchlistedContentIds = useMemo(
    () =>
      Array.from(
        new Set(
          session.interactions
            .filter((interaction) => interaction.interactionType === 'watchlisted')
            .map((interaction) => interaction.contentId),
        ),
      ),
    [session.interactions],
  );
  const watchedContentIds = useMemo(
    () =>
      Array.from(
        new Set(
          session.interactions
            .filter((interaction) => interaction.interactionType === 'watched')
            .map((interaction) => interaction.contentId),
        ),
      ),
    [session.interactions],
  );

  const value: SessionContextValue = {
    ...session,
    isLoading,
    isAuthenticated: Boolean(session.user),
    watchlistedContentIds,
    watchedContentIds,
    login,
    register,
    logout,
    createConversation,
    selectConversation,
    renameConversation,
    deleteConversation,
    addMessage,
    updateUser,
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
