import { useMemo } from 'react';
import { flattenReviews } from '../utils/flattenReviews';

const DAY_MS = 24 * 60 * 60 * 1000;

function withinLastDays(postDate, days, now) {
  const parsed = new Date(postDate);
  if (Number.isNaN(parsed.getTime())) return false;
  return now.getTime() - parsed.getTime() <= days * DAY_MS;
}

function computeStats(reviews) {
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

  return { total: reviews.length, scopeCounts, sentimentCounts, sourceCounts };
}

// Filters and sorts the flattened review set, and computes summary stats for
// exactly that filtered set, so summary cards and the review list always
// agree on what is currently on screen.
export function useFilteredData(data, filters) {
  return useMemo(() => {
    const now = new Date();
    let reviews = flattenReviews(data);

    if (filters.date === '7d') {
      reviews = reviews.filter((r) => withinLastDays(r.post_date, 7, now));
    } else if (filters.date === '30d') {
      reviews = reviews.filter((r) => withinLastDays(r.post_date, 30, now));
    }

    if (filters.source !== 'all') {
      reviews = reviews.filter((r) => r.source === filters.source);
    }

    if (filters.client !== 'all') {
      reviews = reviews.filter((r) => r.client === filters.client);
    }

    if (filters.scope !== 'all') {
      const scopeValue = { in: 'true', unsure: 'unsure' }[filters.scope];
      reviews = reviews.filter((r) => r.valify_scope === scopeValue);
    }

    reviews = [...reviews].sort((a, b) => new Date(b.post_date) - new Date(a.post_date));

    return { reviews, stats: computeStats(reviews) };
  }, [data, filters]);
}
