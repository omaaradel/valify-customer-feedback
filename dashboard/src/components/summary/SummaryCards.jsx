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

function SummaryCards({ reviews }) {
  const total = reviews.length;

  const scopeCounts = { inScope: 0, outOfScope: 0, unsure: 0 };
  const sentimentCounts = { positive: 0, neutral: 0, negative: 0 };
  const sourceCounts = { appstore: 0, play_store: 0 };

  for (const review of reviews) {
    if (review.valify_scope === 'true') scopeCounts.inScope += 1;
    else if (review.valify_scope === 'false') scopeCounts.outOfScope += 1;
    else if (review.valify_scope === 'unsure') scopeCounts.unsure += 1;

    if (review.sentiment === 'positive') sentimentCounts.positive += 1;
    else if (review.sentiment === 'neutral') sentimentCounts.neutral += 1;
    else if (review.sentiment === 'negative') sentimentCounts.negative += 1;

    if (review.source === 'appstore') sourceCounts.appstore += 1;
    else if (review.source === 'play_store') sourceCounts.play_store += 1;
  }

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
