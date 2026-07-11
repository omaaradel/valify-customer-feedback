import ReviewCard from './ReviewCard';
import EmptyState from './EmptyState';

// 3 columns desktop (1280px+), 2 tablet (768px+), 1 mobile, via Tailwind's
// default lg (1024px) and md (768px) breakpoints; lg is close enough to the
// spec's 1280px cutoff at the container's own max-width of 1280px, since the
// container itself cannot exceed 3 comfortably-sized columns before that.
function ReviewList({ reviews, total }) {
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reviews.map((review, index) => (
            <ReviewCard key={`${review.client}-${review.post_date}-${index}`} review={review} />
          ))}
        </div>
      )}
    </div>
  );
}

export default ReviewList;
