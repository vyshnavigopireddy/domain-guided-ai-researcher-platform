import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

const CLUSTER_COLORS = {
  'Cryptography & Security': '#6366f1',
  'Machine Learning & AI': '#10b981',
  'Algorithms & Theory': '#f59e0b',
  'Distributed & Systems': '#3b82f6',
  'Database & Information Retrieval': '#8b5cf6',
  'Programming Languages & Software': '#ec4899',
  'Bioinformatics & Computational Biology': '#14b8a6',
  'Computer Vision & Graphics': '#f97316',
  'Human-Computer Interaction': '#06b6d4',
  'Quantum Computing': '#a855f7',
  'Uncategorized': '#9ca3af',
};

export default function ClustersPage() {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [researchers, setResearchers] = useState([]);
  const [loadingResearchers, setLoadingResearchers] = useState(false);

  useEffect(() => {
    api.getClusters()
      .then(data => setClusters(data.clusters || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSelectCluster = async (cluster) => {
    if (selected === cluster.cluster) {
      setSelected(null);
      setResearchers([]);
      return;
    }
    setSelected(cluster.cluster);
    setLoadingResearchers(true);
    try {
      const data = await api.getClusterResearchers(cluster.cluster);
      setResearchers(data.researchers || []);
    } catch (e) {
      setResearchers([]);
    } finally {
      setLoadingResearchers(false);
    }
  };

  if (loading) return <div className="page-loading">Loading domain clusters...</div>;
  if (error) return <div className="error-banner">⚠️ {error}</div>;

  const totalResearchers = clusters.reduce((s, c) => s + c.researcher_count, 0);
  const totalPapers = clusters.reduce((s, c) => s + c.paper_count, 0);

  return (
    <div className="page clusters-page">
      <div className="page-hero">
        <h2>Domain Clusters</h2>
        <p>
          {clusters.length} clusters · {totalResearchers} researchers · {totalPapers.toLocaleString()} publications
        </p>
      </div>

      {/* Cluster grid */}
      <div className="cluster-grid">
        {clusters.map((c) => {
          const color = CLUSTER_COLORS[c.cluster] || '#9ca3af';
          const isActive = selected === c.cluster;
          return (
            <div
              key={c.cluster}
              className={`cluster-card ${isActive ? 'active' : ''}`}
              style={{ '--cluster-color': color }}
              onClick={() => handleSelectCluster(c)}
            >
              <div className="cluster-card-header" style={{ borderColor: color }}>
                <h3 className="cluster-name" style={{ color }}>{c.cluster}</h3>
                <span className="cluster-badge">{c.researcher_count} researchers</span>
              </div>
              <div className="cluster-stats">
                <div className="stat">
                  <span className="stat-value">{c.paper_count.toLocaleString()}</span>
                  <span className="stat-label">Papers</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{c.total_citations.toLocaleString()}</span>
                  <span className="stat-label">Citations</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{c.avg_h_index}</span>
                  <span className="stat-label">Avg h-index</span>
                </div>
              </div>
              {c.top_researchers?.length > 0 && (
                <div className="cluster-top-names">
                  {c.top_researchers.slice(0, 3).map(r => (
                    <span key={r.Name} className="researcher-chip">{r.Name}</span>
                  ))}
                </div>
              )}
              <div className="cluster-expand">{isActive ? '▲ Collapse' : '▼ View researchers'}</div>
            </div>
          );
        })}
      </div>

      {/* Researcher detail panel */}
      {selected && (
        <div className="researcher-panel">
          <h3>
            <span style={{ color: CLUSTER_COLORS[selected] || '#9ca3af' }}>●</span>{' '}
            Researchers in "{selected}"
          </h3>
          {loadingResearchers ? (
            <div className="page-loading">Loading...</div>
          ) : (
            <div className="researcher-table-wrapper">
              <table className="researcher-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Affiliation</th>
                    <th>Total Citations</th>
                    <th>h-index</th>
                  </tr>
                </thead>
                <tbody>
                  {researchers.map((r, i) => (
                    <tr key={r.Scholar_ID || i}>
                      <td>{i + 1}</td>
                      <td className="researcher-name">{r.Name}</td>
                      <td>{r.Affiliation}</td>
                      <td>{r.Total_Citations?.toLocaleString()}</td>
                      <td>{r.h_index}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
