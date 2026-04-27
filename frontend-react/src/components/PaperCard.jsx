import React from 'react';

export default function PaperCard({ paper, rank, compact = false }) {
  const score = paper.score ? (paper.score * 100).toFixed(1) : null;

  if (compact) {
    return (
      <div className="paper-card paper-card-compact">
        <span className="paper-rank">[{rank}]</span>
        <div>
          <p className="paper-title-compact">{paper.publication_title}</p>
          <p className="paper-meta-compact">
            {paper.author} · {paper.year} · {paper.citations?.toLocaleString()} citations
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="paper-card">
      <div className="paper-card-header">
        <span className="paper-rank-badge">#{rank}</span>
        {paper.cluster && (
          <span className="paper-cluster-tag">{paper.cluster}</span>
        )}
        {score && (
          <span className="paper-score" title="Semantic similarity score">
            {score}% match
          </span>
        )}
      </div>
      <h4 className="paper-title">{paper.publication_title}</h4>
      <div className="paper-author">
        <span className="author-name">👤 {paper.author}</span>
        {paper.affiliation && (
          <span className="author-affiliation"> · {paper.affiliation}</span>
        )}
      </div>
      <div className="paper-stats">
        {paper.year && (
          <span className="stat-chip">📅 {Math.round(paper.year)}</span>
        )}
        <span className="stat-chip">📊 {paper.citations?.toLocaleString() ?? 0} citations</span>
        {paper.h_index && (
          <span className="stat-chip">h-index: {paper.h_index}</span>
        )}
      </div>
      {paper.interests && (
        <p className="paper-interests">🏷 {paper.interests}</p>
      )}
    </div>
  );
}
