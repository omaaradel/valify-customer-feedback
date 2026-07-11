import { useEffect, useState } from 'react';
import config from './config';
import { flattenReviews } from './utils/flattenReviews';
import Header from './components/layout/Header';
import PageContainer from './components/layout/PageContainer';
import SummaryCards from './components/summary/SummaryCards';

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(config.dataUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load feedback data (${res.status})`);
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  const reviews = data ? flattenReviews(data) : [];

  return (
    <div style={{ background: 'var(--color-bg)', minHeight: '100vh' }}>
      <Header />
      <PageContainer>
        {error && (
          <p style={{ color: 'var(--color-negative)' }}>Could not load feedback data: {error}</p>
        )}
        {data && <SummaryCards reviews={reviews} />}
      </PageContainer>
    </div>
  );
}

export default App;
