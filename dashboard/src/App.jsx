import { useEffect, useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import config from './config';
import { AuthProvider } from './context/AuthContext';
import { useFilteredData } from './hooks/useFilteredData';
import { flattenReviews } from './utils/flattenReviews';
import Header from './components/layout/Header';
import PageContainer from './components/layout/PageContainer';
import ConfidenceBanner from './components/layout/ConfidenceBanner';
import SummaryCards from './components/summary/SummaryCards';
import FilterBar, { DEFAULT_FILTERS } from './components/filters/FilterBar';
import ReviewList from './components/reviews/ReviewList';

function Dashboard() {
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
            <ConfidenceBanner />
            <FilterBar data={data} filters={filters} onChange={handleFilterChange} onReset={handleReset} />
            <ReviewList reviews={reviews} total={totalUnfiltered} filterKey={JSON.stringify(filters)} />
          </>
        )}
      </PageContainer>
    </div>
  );
}

function App() {
  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <Dashboard />
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
