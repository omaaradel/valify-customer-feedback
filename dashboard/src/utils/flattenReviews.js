// Flattens feedback.json's { generated_at, total_rows, clients } shape into a
// single array of reviews, each tagged with its client name, so summary stats
// and the review list can work from one shape instead of walking the client
// map every time.
export function flattenReviews(data) {
  const reviews = [];
  for (const [client, bucket] of Object.entries(data?.clients || {})) {
    for (const review of bucket?.reviews || []) {
      reviews.push({ ...review, client });
    }
  }
  return reviews;
}
