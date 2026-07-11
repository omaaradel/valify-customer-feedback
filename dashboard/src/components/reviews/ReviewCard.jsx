import { useEffect, useRef, useState } from 'react';
import ClientAvatar from './ClientAvatar';
import Badge from './Badge';

const SOURCE_BADGE = {
  play_store: { variant: 'source-playstore', label: 'Play Store' },
  appstore: { variant: 'source-appstore', label: 'App Store' },
};

const SCOPE_BADGE = {
  true: { variant: 'scope-true', label: 'In scope' },
  false: { variant: 'scope-false', label: 'Out of scope' },
  unsure: { variant: 'scope-unsure', label: 'Unsure' },
};

const SENTIMENT_BADGE = {
  positive: { variant: 'sentiment-positive', label: 'Positive' },
  negative: { variant: 'sentiment-negative', label: 'Negative' },
  neutral: { variant: 'sentiment-neutral', label: 'Neutral' },
};

const PRODUCT_AREA_LABEL = {
  nid_verification: 'NID Verification',
  liveness_detection: 'Liveness Detection',
  facematch: 'Facematch',
  onboarding_general: 'Onboarding',
  other: 'Other',
};

function formatDate(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value || '';
  return parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

function ReviewCard({ review, delayMs = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);
  const textRef = useRef(null);

  const text = review.raw_text || '';
  const sourceBadge = SOURCE_BADGE[review.source];
  const scopeBadge = SCOPE_BADGE[review.valify_scope];
  const sentimentBadge = SENTIMENT_BADGE[review.sentiment];
  const productAreaLabel = review.product_area && review.product_area !== 'other'
    ? PRODUCT_AREA_LABEL[review.product_area] || review.product_area
    : null;

  useEffect(() => {
    setExpanded(false);
    const el = textRef.current;
    if (el) setOverflowing(el.scrollHeight > el.clientHeight + 1);
  }, [text]);

  return (
    <div
      className="review-card bg-white"
      style={{
        '--review-card-delay': `${delayMs}ms`,
        borderRadius: 'var(--radius-card)',
        padding: 'var(--card-padding)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <ClientAvatar client={review.client} />
          <div>
            <div
              style={{
                fontSize: 'var(--font-size-card-text)',
                fontWeight: 'var(--font-weight-heading)',
                color: 'var(--color-text-primary)',
                lineHeight: 'var(--line-height-heading)',
              }}
            >
              {review.client}
            </div>
            <div
              style={{
                fontSize: 'var(--font-size-caption)',
                color: 'var(--color-text-secondary)',
              }}
            >
              Client
            </div>
          </div>
        </div>
        <div
          style={{
            fontSize: 'var(--font-size-caption)',
            color: 'var(--color-text-secondary)',
            whiteSpace: 'nowrap',
          }}
        >
          {formatDate(review.post_date)}
        </div>
      </div>

      {sourceBadge && (
        <div className="mt-3">
          <Badge variant={sourceBadge.variant}>{sourceBadge.label}</Badge>
        </div>
      )}

      <p
        ref={textRef}
        dir="auto"
        className="mt-3"
        style={{
          fontSize: 'var(--font-size-card-text)',
          color: 'var(--color-text-primary)',
          lineHeight: 'var(--line-height-body)',
          display: expanded ? 'block' : '-webkit-box',
          WebkitLineClamp: expanded ? 'unset' : 4,
          WebkitBoxOrient: 'vertical',
          overflow: expanded ? 'visible' : 'hidden',
        }}
      >
        {text}
      </p>
      {overflowing && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          style={{
            marginTop: '4px',
            fontSize: 'var(--font-size-caption)',
            fontWeight: 'var(--font-weight-label)',
            color: 'var(--color-teal)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
          }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {productAreaLabel && <Badge variant="product-area">{productAreaLabel}</Badge>}
        {scopeBadge && <Badge variant={scopeBadge.variant}>{scopeBadge.label}</Badge>}
        {sentimentBadge && <Badge variant={sentimentBadge.variant}>{sentimentBadge.label}</Badge>}
      </div>
    </div>
  );
}

export default ReviewCard;
