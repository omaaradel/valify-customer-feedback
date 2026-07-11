import ReviewCard from './ReviewCard';
import EmptyState from './EmptyState';

const STAGGER_MS = 50;
const MAX_STAGGER_MS = 500; // caps the delay so large result sets do not make the tail feel sluggish

// 3 columns desktop (1280px+), 2 tablet (768px+), 1 mobile, using Tailwind's
// xl (1280px) and md (768px) breakpoints exactly, matching the spec's stated
// cutoffs rather than Tailwind's default lg (1024px).
//
// `filterKey` should change whenever the active filters change (see App.jsx).
// It is folded into each card's React key so the whole grid remounts, and
// therefore replays its fade-in animation, on every filter change, not just
// on first load.
function ReviewList({ reviews, total, filterKey }) {
  return (
    <div>
      <div className="mb-3 flex justify-end">
        <span style={{ fontSize: 'var(--font-size-caption)', color: 'var(--color-text-secondary)' }}>
          {reviews.length} of {total} reviews
        </span>
      </div>
      {reviews.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {reviews.map((review, index) => (
            <ReviewCard
              key={`${filterKey}-${review.client}-${review.post_date}-${index}`}
              review={review}
              delayMs={Math.min(index * STAGGER_MS, MAX_STAGGER_MS)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ReviewList;
