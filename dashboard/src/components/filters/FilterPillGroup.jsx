// One labeled group of filter pills. `options` is an array of { value, label }.
function FilterPillGroup({ label, options, active, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      <span
        style={{
          fontSize: 'var(--font-size-caption)',
          fontWeight: 'var(--font-weight-label)',
          letterSpacing: '0.05em',
          color: 'var(--color-text-secondary)',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </span>
      <div className="flex flex-wrap" style={{ gap: 'var(--filter-pill-gap)' }}>
        {options.map((option) => {
          const isActive = option.value === active;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              aria-pressed={isActive}
              style={{
                borderRadius: 'var(--radius-pill)',
                padding: '6px 14px',
                fontSize: 'var(--font-size-body)',
                fontWeight: 'var(--font-weight-label)',
                border: isActive ? 'none' : '1px solid var(--color-border)',
                background: isActive ? 'var(--color-teal)' : 'var(--color-surface)',
                color: isActive ? '#FFFFFF' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                transition: 'background 150ms ease-out, color 150ms ease-out',
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default FilterPillGroup;
