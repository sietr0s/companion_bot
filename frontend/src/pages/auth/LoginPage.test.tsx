import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AuthService } from '../../api/generated';
import { LoginPage } from './LoginPage';

const { setToken, navigate } = vi.hoisted(() => ({ setToken: vi.fn(), navigate: vi.fn() }));
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => ({ token: null, setToken }) }));
vi.mock('react-router-dom', () => ({ useNavigate: () => navigate }));
vi.mock('../../components/layout/AuthLayout', () => ({
  AuthLayout: ({ children }: { children: React.ReactNode }) => children,
}));

window.matchMedia = vi
  .fn()
  .mockImplementation(() => ({ matches: false, addListener: vi.fn(), removeListener: vi.fn() }));

describe('LoginPage', () => {
  it('submits credentials and opens the dashboard after successful login', async () => {
    const login = vi
      .spyOn(AuthService, 'loginApiV1PublicAuthLoginPost')
      .mockResolvedValue({ access_token: 'test-token', token_type: 'bearer' });
    try {
      render(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
          <LoginPage />
        </QueryClientProvider>
      );
      fireEvent.change(screen.getByLabelText('Identifier'), { target: { value: 'admin@example.com' } });
      fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'test-password' } });
      fireEvent.click(screen.getByRole('button', { name: 'Войти' }));
      await waitFor(() => expect(setToken).toHaveBeenCalledWith('test-token'));
      expect(login).toHaveBeenCalledWith({ identifier: 'admin@example.com', password: 'test-password' });
      expect(navigate).toHaveBeenCalledWith('/dashboard');
    } finally {
      login.mockRestore();
    }
  });
});
