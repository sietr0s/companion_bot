import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { ProtectedLayout } from './components/layout/ProtectedLayout';
import { LoginPage } from './pages/auth/LoginPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { UsersPage } from './pages/users/UsersPage';
import { TelegramAccountsPage } from './pages/telegram/TelegramAccountsPage';
import { TelegramChatsPage } from './pages/telegram/TelegramChatsPage';
import { TelegramSettingsPage } from './pages/telegram/TelegramSettingsPage';
import { MemoryPage } from './pages/memory/MemoryPage';
import { InstagramAccountsPage } from './pages/instagram/InstagramAccountsPage';

function ProtectedRoute() {
  const { token } = useAuth();
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <ProtectedLayout />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="telegram" element={<TelegramAccountsPage />} />
          <Route path="telegram/:accountId/chats" element={<TelegramChatsPage />} />
          <Route path="telegram/:accountId/settings" element={<TelegramSettingsPage />} />
          <Route path="instagram" element={<InstagramAccountsPage />} />
          <Route path="memory" element={<MemoryPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
