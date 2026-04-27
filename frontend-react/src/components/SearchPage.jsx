import React, { useState, useCallback } from 'react';
import { api } from '../api/client';
import PaperCard from './PaperCard';
import SearchFilters from './SearchFilters';

const EXAMPLE_QUERIES = [
  'cryptographic lattice-based encryption schemes',
  'deep learning for natural language processing',
  'distributed consensus fault tolerant systems',
  'graph algorithms parameterized complexity',
  'quantum computing error correction',
];

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ topK: 8, clusterFilter: '', minCitations: '' });
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async (q = query) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await api.search(
        q.trim(),
        filters.topK,
        filters.clusterFilter || null,
        filters.minCitations ? parseInt(filters.minCitations) : null
      );
      setResults(data.results || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [query, filters]);

  const handleExampleClick = (q) => {
    setQuery(q);
    handleSearch(q);
  };

  return (
    <div className="page search-page">
      <div className="page-hero">
        <h2>Semantic Research Search</h2>
        <p>
          Search by <strong>meaning</strong>, not keywords. Powered by sentence embeddings + FAISS vector search.
        </p>
      </div>

      {/* Search bar */}
      <div className="search-bar-wrapper">
        <div className="search-bar">
          <input
            type="text"
            className="search-input"
            placeholder="e.g. homomorphic encryption for cloud computing..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            className="btn btn-primary search-btn"
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
          >
            {loading ? <span className="spinner" /> : '🔍 Search'}
          </button>
        </div>

        <SearchFilters filters={filters} onChange={setFilters} />
      </div>

      {/* Example queries */}
      {!searched && (
        <div className="examples">
          <p className="examples-label">Try an example:</p>
          <div className="example-pills">
            {EXAMPLE_QUERIES.map((q) => (
              <button key={q} className="pill" onClick={() => handleExampleClick(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {error && <div className="error-banner">⚠️ {error}</div>}

      {/* Results */}
      {searched && !loading && (
        <div className="results-section">
          <div className="results-header">
            <span className="results-count">
              {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
            </span>
            {results.length === 0 && <p className="no-results">No matching papers found. Try a broader query.</p>}
          </div>
          <div className="results-grid">
            {results.map((paper, i) => (
              <PaperCard key={i} paper={paper} rank={i + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
