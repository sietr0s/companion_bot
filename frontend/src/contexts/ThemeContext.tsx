import { ConfigProvider, theme, type ThemeConfig } from 'antd';
import { createContext, useContext, useState, type ReactNode } from 'react';

type ThemeMode = 'dark' | 'light';

type ThemeContextValue = {
  mode: ThemeMode;
  toggleTheme: () => void;
  config: ThemeConfig;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 10,
  },
};

const lightTheme: ThemeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 10,
  },
};

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>('dark');

  const value: ThemeContextValue = {
    mode,
    toggleTheme: () => setMode((prev) => (prev === 'dark' ? 'light' : 'dark')),
    config: mode === 'dark' ? darkTheme : lightTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      <ConfigProvider theme={value.config}>{children}</ConfigProvider>
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used inside ThemeProvider');
  }
  return context;
}