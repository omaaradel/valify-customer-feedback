// Small pill badge. Background is a 10% tint of the variant's color, text is
// the full color, consistent with the colored numbers used in SummaryCards.
const VARIANT_COLORS = {
  'source-playstore': 'var(--color-blue)',
  'source-appstore': 'var(--color-purple)',
  'scope-true': 'var(--color-in-scope)',
  'scope-false': 'var(--color-out-scope)',
  'scope-unsure': 'var(--color-unsure)',
  'sentiment-positive': 'var(--color-positive)',
  'sentiment-negative': 'var(--color-negative)',
  'sentiment-neutral': 'var(--color-neutral)',
  'product-area': 'var(--color-supporting)',
};

function Badge({ variant, children }) {
  const color = VARIANT_COLORS[variant] || 'var(--color-text-secondary)';
  return (
    <span
      style={{
        display: 'inline-block',
        borderRadius: 'var(--radius-badge)',
        padding: '2px 10px',
        fontSize: 'var(--font-size-caption)',
        fontWeight: 'var(--font-weight-label)',
        color,
        background: `color-mix(in srgb, ${color} 10%, transparent)`,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
