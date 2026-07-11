import FilterPillGroup from './FilterPillGroup';

export const DEFAULT_FILTERS = { date: 'all', source: 'all', client: 'all', scope: 'all' };

const DATE_OPTIONS = [
  { value: 'all', label: 'All time' },
  { value: '30d', label: 'Last 30 days' },
  { value: '7d', label: 'Last 7 days' },
];

const SOURCE_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'appstore', label: 'App Store' },
  { value: 'play_store', label: 'Play Store' },
];

const SCOPE_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'in', label: 'In scope' },
  { value: 'out', label: 'Out of scope' },
  { value: 'unsure', label: 'Unsure' },
];

function FilterBar({ data, filters, onChange, onReset }) {
  const clientOptions = [
    { value: 'all', label: 'All' },
    ...Object.entries(data?.clients || {})
      .filter(([, bucket]) => (bucket?.reviews?.length || 0) > 0)
      .map(([client]) => ({ value: client, label: client })),
  ];

  return (
    <div
      className="bg-white"
      style={{
        borderRadius: 'var(--radius-card)',
        padding: 'var(--card-padding)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 'var(--filter-group-gap)' }}>
        <div className="flex flex-wrap" style={{ gap: 'var(--filter-group-gap)' }}>
          <FilterPillGroup
            label="Date"
            options={DATE_OPTIONS}
            active={filters.date}
            onChange={(value) => onChange('date', value)}
          />
          <FilterPillGroup
            label="Source"
            options={SOURCE_OPTIONS}
            active={filters.source}
            onChange={(value) => onChange('source', value)}
          />
          <FilterPillGroup
            label="Client"
            options={clientOptions}
            active={filters.client}
            onChange={(value) => onChange('client', value)}
          />
          <FilterPillGroup
            label="Scope"
            options={SCOPE_OPTIONS}
            active={filters.scope}
            onChange={(value) => onChange('scope', value)}
          />
        </div>
        <button
          type="button"
          onClick={onReset}
          style={{
            fontSize: 'var(--font-size-body)',
            fontWeight: 'var(--font-weight-label)',
            color: 'var(--color-text-secondary)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            textDecoration: 'underline',
            padding: 0,
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          Reset filters
        </button>
      </div>
    </div>
  );
}

export default FilterBar;
