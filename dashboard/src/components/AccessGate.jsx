function AccessGate() {
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
          This dashboard is currently unavailable. If you believe you should have access, please
          contact your Valify account manager.
        </p>
      </div>
    </div>
  );
}

export default AccessGate;
