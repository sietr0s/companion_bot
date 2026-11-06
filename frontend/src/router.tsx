import { lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { ProtectedLayout } from './components/layout/ProtectedLayout';
import { LoginPage } from './pages/auth/LoginPage';
const DashboardPage = lazy(() =>
  import('./pages/dashboard/DashboardPage').then((module) => ({ default: module.DashboardPage }))
);
const UsersPage = lazy(() => import('./pages/users/UsersPage').then((module) => ({ default: module.UsersPage })));
const TelegramAccountsPage = lazy(() =>
  import('./pages/telegram/TelegramAccountsPage').then((module) => ({ default: module.TelegramAccountsPage }))
);
const TelegramChatsPage = lazy(() =>
  import('./pages/telegram/TelegramChatsPage').then((module) => ({ default: module.TelegramChatsPage }))
);
const TelegramSettingsPage = lazy(() =>
  import('./pages/telegram/TelegramSettingsPage').then((module) => ({ default: module.TelegramSettingsPage }))
);
const MemoryPage = lazy(() => import('./pages/memory/MemoryPage').then((module) => ({ default: module.MemoryPage })));
const InstagramAccountsPage = lazy(() =>
  import('./pages/instagram/InstagramAccountsPage').then((module) => ({ default: module.InstagramAccountsPage }))
);

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
