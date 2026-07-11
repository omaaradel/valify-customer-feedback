// Shown when the current filters match nothing.
function EmptyState() {
  return (
    <div
      className="flex flex-col items-center justify-center text-center"
      style={{ padding: '64px 24px', color: 'var(--color-text-secondary)' }}
    >
      <p style={{ fontSize: 'var(--font-size-card-title)', fontWeight: 'var(--font-weight-heading)' }}>
        No feedback matches these filters.
      </p>
      <p className="mt-2" style={{ fontSize: 'var(--font-size-body)' }}>
        Try adjusting your selection.
      </p>
    </div>
  );
}

export default EmptyState;
