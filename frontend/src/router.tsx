import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { ProtectedLayout } from './components/layout/ProtectedLayout';
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { ChangePasswordPage } from './pages/auth/ChangePasswordPage';
import { DeleteAccountPage } from './pages/auth/DeleteAccountPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { UsersPage } from './pages/users/UsersPage';
import { MediaPage } from './pages/media/MediaPage';
import { TelegramPage } from './pages/telegram/TelegramPage';
import { ClassifierPage } from './pages/classifier/ClassifierPage';
import { TemplatesPage } from './pages/notifications/TemplatesPage';
import { HistoryPage } from './pages/notifications/HistoryPage';
import { JobMatcherPage } from './pages/jobMatcher/JobMatcherPage';

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
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<ProtectedRoute />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="change-password" element={<ChangePasswordPage />} />
          <Route path="delete-account" element={<DeleteAccountPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="media" element={<MediaPage />} />
          <Route path="telegram" element={<TelegramPage />} />
          <Route path="classifier/categories" element={<ClassifierPage />} />
          <Route path="notifications/templates" element={<TemplatesPage />} />
          <Route path="notifications/history" element={<HistoryPage />} />
          <Route path="job-matcher/subscriptions" element={<JobMatcherPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
