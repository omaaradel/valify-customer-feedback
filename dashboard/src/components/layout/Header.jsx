import { useAuth } from '../../context/AuthContext';

// Dark hero header: navy to teal-tinted navy gradient, a restrained diagonal
// accent echoing the logo's own angular checkmark, logo top-left, page title.
// No navigation links in Phase 10, this becomes a real app header when the
// dashboard grows internal tooling in a later phase.
function Header() {
  const { email, logout } = useAuth();

  return (
    <header
      className="relative overflow-hidden px-4 py-8 md:px-8 md:py-10"
      style={{
        background:
          'linear-gradient(120deg, var(--color-navy) 0%, color-mix(in srgb, var(--color-navy) 55%, var(--color-teal) 45%) 100%)',
      }}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-0 w-1/2"
        style={{
          background: 'color-mix(in srgb, var(--color-teal) 16%, transparent)',
          clipPath: 'polygon(45% 0, 100% 0, 100% 100%, 15% 100%)',
        }}
      />
      <div className="relative mx-auto flex flex-col" style={{ maxWidth: '1280px', gap: 'var(--space-3)' }}>
        <div className="flex items-start justify-between" style={{ gap: 'var(--space-2)' }}>
          <img src="/valify-logo-white.png" alt="Valify" className="h-8 w-auto md:h-9" />
          <div
            className="flex items-center"
            style={{ gap: 'var(--space-2)', flexShrink: 0, whiteSpace: 'nowrap' }}
          >
            <span
              style={{
                color: '#FFFFFF',
                opacity: 0.75,
                fontSize: 'var(--font-size-caption)',
                fontWeight: 'var(--font-weight-body)',
              }}
            >
              {email}
            </span>
            <button
              type="button"
              onClick={logout}
              style={{
                color: '#FFFFFF',
                opacity: 0.9,
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                textDecoration: 'underline',
                padding: 0,
                fontSize: 'var(--font-size-caption)',
                fontWeight: 'var(--font-weight-label)',
              }}
            >
              Sign out
            </button>
          </div>
        </div>
        <div className="flex flex-col items-start">
          <h1
            style={{
              color: '#FFFFFF',
              fontSize: 'var(--font-size-page-title)',
              fontWeight: 'var(--font-weight-page-title)',
              lineHeight: 'var(--line-height-heading)',
              margin: 0,
            }}
          >
            Customer Feedback Portal
          </h1>
          <p
            style={{
              color: 'var(--color-supporting)',
              fontSize: 'var(--font-size-body)',
              fontWeight: 'var(--font-weight-body)',
              lineHeight: 'var(--line-height-body)',
              margin: 0,
            }}
          >
            Maintained by Omar Farghaly, Associate Product Manager
          </p>
        </div>
      </div>
    </header>
  );
}

export default Header;
