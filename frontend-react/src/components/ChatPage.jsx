import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import PaperCard from './PaperCard';

function EvalBadge({ metrics }) {
  if (!metrics) return null;
  const score = metrics.overall_score ?? 0;
  const color = score >= 0.7 ? '#22c55e' : score >= 0.4 ? '#f59e0b' : '#ef4444';
  return (
    <div className="eval-badge">
      <span style={{ fontSize: 11, color: '#888' }}>Quality: </span>
      <span style={{ fontSize: 12, fontWeight: 700, color }}>{(score * 100).toFixed(0)}%</span>
      <span style={{ fontSize: 10, color: '#aaa', marginLeft: 6 }}>
        faith={((metrics.faithfulness ?? 0) * 100).toFixed(0)}%
        {' · '}rel={((metrics.answer_relevance ?? 0) * 100).toFixed(0)}%
        {' · '}{(metrics.latency_ms ?? 0).toFixed(0)}ms
      </span>
      {metrics.flags?.length > 0 && (
        <span style={{ marginLeft: 8, color: '#f59e0b', fontSize: 10 }}>
          ⚠️ {metrics.flags.join(', ')}
        </span>
      )}
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  'Who are the top researchers in cryptography?',
  'Suggest papers on deep learning for NLP',
  'Find similar papers to homomorphic encryption',
  'What are key topics in distributed systems research?',
  'Which researchers work on quantum computing?',
];

export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "👋 Hello! I'm your AI research assistant. I can answer questions about researchers, suggest papers, find domain experts, and more — all grounded in the actual research database.\n\nWhat would you like to know?",
      sources: [],
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSources, setShowSources] = useState({});
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getChatHistory = () =>
    messages
      .filter((m, i) => i > 0)   // skip the initial assistant greeting at index 0
      .slice(-6)
      .map(m => ({ role: m.role, content: m.content }));

  const handleSend = async (text = input) => {
    if (!text.trim() || loading) return;
    const userMsg = { role: 'user', content: text.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const data = await api.chat(text.trim(), getChatHistory());
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        evaluation: data.evaluation || null,
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${e.message}`,
        sources: [],
        evaluation: null,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (idx) => {
    setShowSources(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="page chat-page">
      <div className="chat-container">
        {/* Suggested questions */}
        {messages.length === 1 && (
          <div className="suggested-questions">
            <p className="sq-label">💡 Suggested questions</p>
            <div className="sq-grid">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button key={q} className="sq-btn" onClick={() => handleSend(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content-wrapper">
                <div className="message-bubble">
                  <pre className="message-text">{msg.content}</pre>
                </div>

                {/* Eval metrics */}
                {msg.role === 'assistant' && <EvalBadge metrics={msg.evaluation} />}

                {/* Sources toggle */}
                {msg.role === 'assistant' && msg.sources?.length > 0 && (
                  <div className="sources-section">
                    <button
                      className="sources-toggle"
                      onClick={() => toggleSources(idx)}
                    >
                      📎 {showSources[idx] ? 'Hide' : 'Show'} {msg.sources.length} source paper{msg.sources.length !== 1 ? 's' : ''}
                    </button>
                    {showSources[idx] && (
                      <div className="sources-list">
                        {msg.sources.map((s, si) => (
                          <PaperCard key={si} paper={s} rank={si + 1} compact />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="message message-assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-bubble typing-bubble">
                <span className="dot" /><span className="dot" /><span className="dot" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="chat-input-bar">
          <input
            className="chat-input"
            placeholder="Ask about researchers, papers, domains..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            {loading ? <span className="spinner" /> : '↑ Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
