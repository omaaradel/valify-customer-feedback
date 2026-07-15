import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';

const NOT_AUTHORIZED_MESSAGE =
  'Your account is not authorized to access this dashboard. Contact your Valify account manager.';
const GENERIC_ERROR_MESSAGE = 'Sign-in failed. Please try again.';

function AccessGate({ onAuthenticated }) {
  const [error, setError] = useState(null);

  const handleSuccess = async (credentialResponse) => {
    setError(null);
    try {
      const res = await fetch('/api/auth/verify', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential }),
      });

      if (res.ok) {
        const data = await res.json();
        onAuthenticated(data.email);
        return;
      }

      if (res.status === 403) {
        setError(NOT_AUTHORIZED_MESSAGE);
        return;
      }

      setError(GENERIC_ERROR_MESSAGE);
    } catch {
      setError(GENERIC_ERROR_MESSAGE);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4 py-8 md:px-8"
      style={{
        background:
          'linear-gradient(120deg, var(--color-navy) 0%, color-mix(in srgb, var(--color-navy) 55%, var(--color-teal) 45%) 100%)',
      }}
    >
      <div
        className="flex flex-col items-center text-center"
        style={{ maxWidth: '480px', gap: 'var(--space-3)' }}
      >
        <img src="/valify-logo-white.png" alt="Valify" className="h-8 w-auto md:h-9" />
        <h1
          style={{
            color: '#FFFFFF',
            fontSize: 'var(--font-size-page-title)',
            fontWeight: 'var(--font-weight-page-title)',
            lineHeight: 'var(--line-height-heading)',
            margin: 0,
          }}
        >
          Access Restricted
        </h1>
        <p
          style={{
            color: '#FFFFFF',
            opacity: 0.8,
            fontSize: 'var(--font-size-card-text)',
            fontWeight: 'var(--font-weight-body)',
            lineHeight: 'var(--line-height-body)',
            margin: 0,
          }}
        >
          Sign in with your Valify Google account to continue.
        </p>
        <div>
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={() => setError(GENERIC_ERROR_MESSAGE)}
            locale="en"
          />
        </div>
        {error && (
          <p
            style={{
              color: '#FFFFFF',
              background: 'color-mix(in srgb, var(--color-negative) 35%, transparent)',
              borderRadius: 'var(--radius-badge)',
              padding: 'var(--space-1) var(--space-2)',
              fontSize: 'var(--font-size-body)',
              fontWeight: 'var(--font-weight-body)',
              lineHeight: 'var(--line-height-body)',
              margin: 0,
            }}
          >
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

export default AccessGate;
