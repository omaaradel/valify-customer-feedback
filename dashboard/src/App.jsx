import { useEffect, useState } from 'react';
import config from './config';
import { useFilteredData } from './hooks/useFilteredData';
import { flattenReviews } from './utils/flattenReviews';
import Header from './components/layout/Header';
import PageContainer from './components/layout/PageContainer';
import SummaryCards from './components/summary/SummaryCards';
import FilterBar, { DEFAULT_FILTERS } from './components/filters/FilterBar';
import ReviewList from './components/reviews/ReviewList';

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  useEffect(() => {
    fetch(config.dataUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load feedback data (${res.status})`);
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  const { reviews, stats } = useFilteredData(data || {}, filters);
  const totalUnfiltered = data ? flattenReviews(data).length : 0;

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleReset = () => setFilters(DEFAULT_FILTERS);

  return (
    <div style={{ background: 'var(--color-bg)', minHeight: '100vh' }}>
      <Header />
      <PageContainer>
        {error && (
          <p style={{ color: 'var(--color-negative)' }}>Could not load feedback data: {error}</p>
        )}
        {data && (
          <>
            <SummaryCards stats={stats} />
            <FilterBar data={data} filters={filters} onChange={handleFilterChange} onReset={handleReset} />
            <ReviewList reviews={reviews} total={totalUnfiltered} />
          </>
        )}
      </PageContainer>
    </div>
  );
}

export default App;
