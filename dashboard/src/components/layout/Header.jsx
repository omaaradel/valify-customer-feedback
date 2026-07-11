// Dark hero header: navy to teal-tinted navy gradient, a restrained diagonal
// accent echoing the logo's own angular checkmark, logo top-left, page title.
// No navigation links in Phase 10, this becomes a real app header when the
// dashboard grows internal tooling in a later phase.
function Header() {
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
      <div className="relative mx-auto flex flex-col items-start gap-3" style={{ maxWidth: '1280px' }}>
        <img src="/valify-logo-white.png" alt="Valify" className="h-8 w-auto md:h-9" />
        <h1
          style={{
            color: '#FFFFFF',
            fontSize: 'var(--font-size-page-title)',
            fontWeight: 'var(--font-weight-page-title)',
            lineHeight: 'var(--line-height-heading)',
          }}
        >
          Customer Feedback Portal
        </h1>
      </div>
    </header>
  );
}

export default Header;
