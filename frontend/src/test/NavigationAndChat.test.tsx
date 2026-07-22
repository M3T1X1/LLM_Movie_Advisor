import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { demoUser, initialAgentSteps, initialMessages } from '../data/mockData';
import { AgentStatus } from '../components/AgentStatus';
import { ChatInterface } from '../components/ChatInterface';
import { EmptyState } from '../components/EmptyState';
import { Navbar } from '../components/Navbar';

describe('navigation and chat components', () => {
  it('navigates from navbar', async () => {
    const user = userEvent.setup();
    const onViewChange = vi.fn();
    render(<Navbar user={demoUser} activeView="recommendations" onViewChange={onViewChange} onLogout={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: /Baza filmów i seriali/i }));
    await user.click(screen.getByRole('button', { name: 'Trendy' }));
    await user.click(screen.getByRole('button', { name: `Menu użytkownika: ${demoUser.username}` }));
    await user.click(screen.getByRole('menuitem', { name: 'Przejdź do profilu' }));
    expect(onViewChange).toHaveBeenNthCalledWith(1, 'catalog');
    expect(onViewChange).toHaveBeenNthCalledWith(2, 'trends');
    expect(onViewChange).toHaveBeenNthCalledWith(3, 'profile');
  });

  it('shows account details and handles closing and logout from the user menu', async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    const onViewChange = vi.fn();
    render(<Navbar user={demoUser} activeView="catalog" onViewChange={onViewChange} onLogout={onLogout} />);
    const avatar = screen.getByRole('button', { name: `Menu użytkownika: ${demoUser.username}` });

    expect(avatar).toHaveAttribute('aria-expanded', 'false');
    await user.click(avatar);
    expect(avatar).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('menu', { name: 'Menu konta' })).toBeInTheDocument();
    expect(screen.getByText(demoUser.email)).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByRole('menu', { name: 'Menu konta' })).not.toBeInTheDocument();

    await user.click(avatar);
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole('menu', { name: 'Menu konta' })).not.toBeInTheDocument();

    await user.click(avatar);
    await user.click(screen.getByRole('menuitem', { name: 'Moja lista' }));
    expect(onViewChange).toHaveBeenCalledWith('saved');

    await user.click(avatar);
    await user.click(screen.getByRole('menuitem', { name: 'Analiza oglądania' }));
    expect(onViewChange).toHaveBeenCalledWith('analytics');

    await user.click(avatar);
    await user.click(screen.getByRole('menuitem', { name: 'Wyloguj się' }));
    expect(onLogout).toHaveBeenCalledOnce();
    expect(screen.queryByRole('menu', { name: 'Menu konta' })).not.toBeInTheDocument();
  });

  it('keeps account destinations out of the primary navigation', () => {
    render(<Navbar user={demoUser} activeView="catalog" onViewChange={vi.fn()} onLogout={vi.fn()} />);

    expect(screen.queryByRole('button', { name: 'Moja lista' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Analiza' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Profil' })).not.toBeInTheDocument();
  });

  it('renders agent progress states', () => {
    render(
      <AgentStatus
        steps={initialAgentSteps.map((step, index) => ({
          ...step,
          status:
            index === 0
              ? 'running'
              : index === 1
                ? 'success'
                : index === 2
                  ? 'failed'
                  : 'pending',
        }))}
      />,
    );
    expect(screen.getByText('Agent Profilowania')).toBeInTheDocument();
    expect(screen.getByText('Analizuje nastrój i intencję')).toBeInTheDocument();
    expect(screen.getByText('Gotowe')).toBeInTheDocument();
    expect(screen.getByText('Błąd')).toBeInTheDocument();
  });

  it('submits a chat message with Enter', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ChatInterface messages={initialMessages} agentSteps={initialAgentSteps} isProcessing={false} onSubmit={onSubmit} />);
    const textbox = screen.getByPlaceholderText('Opisz nastrój, tempo albo motyw...');
    await user.type(textbox, 'Lekki serial{enter}');
    expect(onSubmit).toHaveBeenCalledWith('Lekki serial');
    expect(textbox).toHaveValue('');
  });

  it('fills a suggested prompt without sending it automatically', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ChatInterface messages={[]} agentSteps={initialAgentSteps} isProcessing={false} onSubmit={onSubmit} />);

    await user.click(screen.getByRole('button', { name: 'Lekki serial na dwa wieczory' }));
    expect(screen.getByPlaceholderText('Opisz nastrój, tempo albo motyw...')).toHaveValue(
      'Lekki serial na dwa wieczory',
    );
    expect(onSubmit).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Wyślij wiadomość' }));
    expect(onSubmit).toHaveBeenCalledWith('Lekki serial na dwa wieczory');
  });

  it('keeps a newline on Shift+Enter instead of submitting', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ChatInterface messages={[]} agentSteps={initialAgentSteps} isProcessing={false} onSubmit={onSubmit} />);
    const textbox = screen.getByPlaceholderText('Opisz nastrój, tempo albo motyw...');

    await user.type(textbox, 'Pierwsza linia{shift>}{enter}{/shift}Druga linia');
    expect(textbox).toHaveValue('Pierwsza linia\nDruga linia');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('disables chat input while processing', () => {
    render(<ChatInterface messages={initialMessages} agentSteps={initialAgentSteps} isProcessing onSubmit={vi.fn()} />);
    expect(screen.getByPlaceholderText('Opisz nastrój, tempo albo motyw...')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Wyślij wiadomość' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Lekki serial na dwa wieczory' })).toBeDisabled();
    expect(screen.getByText('Przetwarzanie')).toBeInTheDocument();
  });

  it('empty watchlist leads back to discovery', async () => {
    const user = userEvent.setup();
    const onDiscover = vi.fn();
    render(<EmptyState onDiscover={onDiscover} />);
    await user.click(screen.getByRole('button', { name: 'Znajdź coś dla mnie' }));
    expect(onDiscover).toHaveBeenCalledOnce();
  });
});
