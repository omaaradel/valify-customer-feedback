import StatCard from './StatCard';
import ScopeSplitBar from './ScopeSplitBar';

const SOURCE_LABELS = { appstore: 'App Store', play_store: 'Play Store' };

function BreakdownRow({ items }) {
  return (
    <div className="mt-3 flex flex-wrap gap-4">
      {items.map((item) => (
        <div key={item.label}>
          <div
            style={{
              fontSize: 'var(--font-size-card-title)',
              fontWeight: 'var(--font-weight-heading)',
              color: item.color || 'var(--color-text-primary)',
              lineHeight: 'var(--line-height-heading)',
            }}
          >
            {item.value}
          </div>
          <div
            style={{
              fontSize: 'var(--font-size-caption)',
              color: 'var(--color-text-secondary)',
              fontWeight: 'var(--font-weight-label)',
            }}
          >
            {item.label}
          </div>
        </div>
      ))}
    </div>
  );
}

// Renders the four summary cards from precomputed stats (see
// hooks/useFilteredData.js), so this component only ever displays numbers,
// it never recomputes them, keeping cards and the review list in agreement.
function SummaryCards({ stats }) {
  const { total, scopeCounts, sentimentCounts, sourceCounts } = stats;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Total Feedback" value={total} />

      <StatCard label="Valify Scope Split">
        <ScopeSplitBar counts={scopeCounts} />
      </StatCard>

      <StatCard label="Sentiment">
        <BreakdownRow
          items={[
            { label: 'Positive', value: sentimentCounts.positive, color: 'var(--color-positive)' },
            { label: 'Neutral', value: sentimentCounts.neutral, color: 'var(--color-neutral)' },
            { label: 'Negative', value: sentimentCounts.negative, color: 'var(--color-negative)' },
          ]}
        />
      </StatCard>

      <StatCard label="By Source">
        <BreakdownRow
          items={[
            { label: SOURCE_LABELS.appstore, value: sourceCounts.appstore, color: 'var(--color-purple)' },
            { label: SOURCE_LABELS.play_store, value: sourceCounts.play_store, color: 'var(--color-blue)' },
          ]}
        />
      </StatCard>
    </div>
  );
}

export default SummaryCards;
