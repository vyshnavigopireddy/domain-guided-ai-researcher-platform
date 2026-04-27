import React, { useState } from 'react';
import SearchPage from './components/SearchPage';
import ChatPage from './components/ChatPage';
import ClustersPage from './components/ClustersPage';
import AgentPage from './components/AgentPage';
import './App.css';

const TABS = [
  { id: 'search',   label: '🔍 Semantic Search', desc: 'Find papers by meaning' },
  { id: 'chat',     label: '💬 RAG Chat',         desc: 'Ask research questions' },
  { id: 'agent',    label: '🤖 AI Agent',          desc: 'LangGraph multi-step agent' },
  { id: 'clusters', label: '🗂 Domain Clusters',   desc: 'Browse by field' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('search');

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <span className="brand-icon">🧠</span>
            <div>
              <h1>AI Researcher Profiling Platform</h1>
              <p>RAG · LangGraph Agent · RAGAS Eval · 317 researchers · 52,000+ papers</p>
            </div>
          </div>
          <nav className="tab-nav">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="app-main">
        {activeTab === 'search'   && <SearchPage />}
        {activeTab === 'chat'     && <ChatPage />}
        {activeTab === 'agent'    && <AgentPage />}
        {activeTab === 'clusters' && <ClustersPage />}
      </main>

      <footer className="app-footer">
        <p>
          Built with React · Node.js · FastAPI · FAISS · SentenceTransformers · LangGraph · GPT-4o-mini
        </p>
      </footer>
    </div>
  );
}
