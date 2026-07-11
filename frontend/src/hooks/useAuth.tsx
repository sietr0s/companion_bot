import { createContext, useContext, useEffect, useState } from 'react';
import { OpenAPI } from '../api/generated';

const TOKEN_STORAGE_KEY = 'ms_starter_admin_token';

type AuthContextValue = {
  token: string | null;
  setToken: (value: string | null) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function useStoredToken(): [string | null, (value: string | null) => void] {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));

  const setToken = (value: string | null) => {
    setTokenState(value);
    if (value) {
      localStorage.setItem(TOKEN_STORAGE_KEY, value);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  };
  return [token, setToken];
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useStoredToken();

  useEffect(() => {
    OpenAPI.BASE = '';
    OpenAPI.TOKEN = token ?? undefined;
  }, [token]);

  const value: AuthContextValue = {
    token,
    setToken,
    logout: () => setToken(null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
