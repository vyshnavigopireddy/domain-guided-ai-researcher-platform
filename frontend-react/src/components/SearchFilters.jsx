import React from 'react';

const CLUSTERS = [
  'Cryptography & Security',
  'Machine Learning & AI',
  'Algorithms & Theory',
  'Distributed & Systems',
  'Database & Information Retrieval',
  'Programming Languages & Software',
  'Bioinformatics & Computational Biology',
  'Computer Vision & Graphics',
  'Human-Computer Interaction',
  'Quantum Computing',
];

export default function SearchFilters({ filters, onChange }) {
  return (
    <div className="search-filters">
      <div className="filter-group">
        <label>Results</label>
        <select
          value={filters.topK}
          onChange={(e) => onChange({ ...filters, topK: parseInt(e.target.value) })}
        >
          {[5, 8, 10, 15, 20].map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>
      <div className="filter-group">
        <label>Domain filter</label>
        <select
          value={filters.clusterFilter}
          onChange={(e) => onChange({ ...filters, clusterFilter: e.target.value })}
        >
          <option value="">All domains</option>
          {CLUSTERS.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>
      <div className="filter-group">
        <label>Min citations</label>
        <input
          type="number"
          placeholder="e.g. 100"
          value={filters.minCitations}
          min={0}
          onChange={(e) => onChange({ ...filters, minCitations: e.target.value })}
        />
      </div>
    </div>
  );
}
