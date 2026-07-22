import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ConversationManager } from '../components/ConversationManager';
import { demoConversations } from '../data/mockData';

describe('ConversationManager', () => {
  it('creates and selects conversations without sending a prompt', async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();
    const onSelect = vi.fn();

    render(
      <ConversationManager
        conversations={demoConversations}
        currentConversationId="1"
        onCreate={onCreate}
        onSelect={onSelect}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Nowa rozmowa' }));
    await user.click(screen.getByRole('button', { name: /^Inteligentne sci-fi/ }));

    expect(onCreate).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledWith('2');
  });

  it('renames a conversation', async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();

    render(
      <ConversationManager
        conversations={[demoConversations[0]]}
        currentConversationId="1"
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onRename={onRename}
        onDelete={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Zmień nazwę rozmowy/ }));
    const input = screen.getByLabelText('Nazwa rozmowy');
    await user.clear(input);
    await user.type(input, 'Thrillery na weekend');
    await user.click(screen.getByRole('button', { name: 'Zapisz nazwę rozmowy' }));

    expect(onRename).toHaveBeenCalledWith('1', 'Thrillery na weekend');
  });

  it('requires confirmation before deleting a conversation', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(
      <ConversationManager
        conversations={[demoConversations[0]]}
        currentConversationId="1"
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onRename={vi.fn()}
        onDelete={onDelete}
      />,
    );

    await user.click(screen.getByRole('button', { name: /Usuń rozmowę:/ }));
    expect(screen.getByText('Usunąć rozmowę i jej wiadomości?')).toBeInTheDocument();
    expect(onDelete).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Usuń' }));
    expect(onDelete).toHaveBeenCalledWith('1');
  });

  it('shows an empty state without conversations', () => {
    render(
      <ConversationManager
        conversations={[]}
        currentConversationId={null}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText('Brak rozmów')).toBeInTheDocument();
  });
});
