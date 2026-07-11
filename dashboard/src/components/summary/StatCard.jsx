// Reusable summary card: an ALL CAPS label, an optional single hero number,
// and optional custom content (a breakdown row, a stacked bar) as children.
function StatCard({ label, value, children }) {
  return (
    <div
      className="bg-white"
      style={{
        borderRadius: 'var(--radius-card)',
        padding: 'var(--card-padding)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div
        style={{
          fontSize: 'var(--font-size-caption)',
          fontWeight: 'var(--font-weight-label)',
          letterSpacing: '0.05em',
          color: 'var(--color-text-secondary)',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </div>
      {value != null && (
        <div
          className="mt-2"
          style={{
            fontSize: 'var(--font-size-page-title)',
            fontWeight: 'var(--font-weight-heading)',
            lineHeight: 'var(--line-height-heading)',
            color: 'var(--color-text-primary)',
          }}
        >
          {value}
        </div>
      )}
      {children}
    </div>
  );
}

export default StatCard;
