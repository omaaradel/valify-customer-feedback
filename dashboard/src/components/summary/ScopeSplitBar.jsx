// Horizontal stacked bar showing the in-scope / out-of-scope / unsure split,
// with a legend underneath giving each segment's count.
const SEGMENTS = [
  { key: 'inScope', label: 'In scope', color: 'var(--color-in-scope)' },
  { key: 'outOfScope', label: 'Out of scope', color: 'var(--color-out-scope)' },
  { key: 'unsure', label: 'Unsure', color: 'var(--color-unsure)' },
];

function ScopeSplitBar({ counts }) {
  const total = SEGMENTS.reduce((sum, s) => sum + (counts[s.key] || 0), 0);

  return (
    <div className="mt-3">
      <div
        className="flex w-full overflow-hidden"
        style={{ height: '12px', borderRadius: 'var(--radius-badge)', background: 'var(--color-border)' }}
      >
        {total > 0 &&
          SEGMENTS.map((segment) => {
            const count = counts[segment.key] || 0;
            if (count === 0) return null;
            return (
              <div
                key={segment.key}
                style={{ width: `${(count / total) * 100}%`, background: segment.color }}
                title={`${segment.label}: ${count}`}
              />
            );
          })}
      </div>
      <div className="mt-3 flex flex-wrap gap-3">
        {SEGMENTS.map((segment) => (
          <div key={segment.key} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: segment.color,
                display: 'inline-block',
              }}
            />
            <span
              style={{
                fontSize: 'var(--font-size-caption)',
                color: 'var(--color-text-secondary)',
                fontWeight: 'var(--font-weight-label)',
              }}
            >
              {segment.label}: {counts[segment.key] || 0}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ScopeSplitBar;
