import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './hooks/useAuth';
import { AppRouter } from './router';
import { handleGlobalApiError } from './utils/api';

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleGlobalApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleGlobalApiError,
  }),
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
