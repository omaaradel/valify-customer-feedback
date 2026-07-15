import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import AccessGate from '../components/AccessGate';

const AuthContext = createContext(null);

function LoadingSpinner() {
  return (
    <div
      className="flex min-h-screen items-center justify-center"
      style={{ background: 'var(--color-bg)' }}
    >
      <div
        className="animate-spin rounded-full"
        style={{
          width: '32px',
          height: '32px',
          border: '3px solid var(--color-border)',
          borderTopColor: 'var(--color-teal)',
        }}
      />
    </div>
  );
}

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading');
  const [email, setEmail] = useState(null);

  useEffect(() => {
    fetch('/api/auth/check', { credentials: 'same-origin' })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        setEmail(data.email);
        setStatus('authenticated');
      })
      .catch(() => {
        setStatus('unauthenticated');
      });
  }, []);

  const login = useCallback((nextEmail) => {
    setEmail(nextEmail);
    setStatus('authenticated');
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
    } catch {
      // Clearing local state below is what actually gates the UI; a failed
      // logout call still leaves the httpOnly cookie in place server-side,
      // but the user is dropped back to the gate either way.
    }
    setEmail(null);
    setStatus('unauthenticated');
  }, []);

  if (status === 'loading') {
    return <LoadingSpinner />;
  }

  if (status === 'unauthenticated') {
    return <AccessGate onAuthenticated={login} />;
  }

  return <AuthContext.Provider value={{ email, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an authenticated AuthProvider tree');
  return ctx;
}
