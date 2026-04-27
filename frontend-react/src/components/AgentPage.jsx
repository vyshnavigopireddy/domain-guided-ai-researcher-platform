import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import PaperCard from './PaperCard';

const TOOL_EMOJI = {
  semantic_search: '🔍',
  researcher_profile: '👤',
  cluster_overview: '🗂️',
};

const AGENT_QUESTIONS = [
  'Compare researchers in cryptography vs machine learning',
  'Who is the most cited researcher in distributed systems?',
  'Find experts on RAG and retrieval-augmented generation',
  'What papers combine NLP with bioinformatics?',
];

function EvalBadge({ metrics }) {
  if (!metrics) return null;
  const score = metrics.overall_score ?? 0;
  const color = score >= 0.7 ? '#22c55e' : score >= 0.4 ? '#f59e0b' : '#ef4444';
  return (
    <div className="eval-badge" style={{ marginTop: 8 }}>
      <span style={{ fontSize: 11, color: '#888' }}>Quality: </span>
      <span style={{ fontSize: 12, fontWeight: 700, color }}>{(score * 100).toFixed(0)}%</span>
      <span style={{ fontSize: 10, color: '#aaa', marginLeft: 6 }}>
        faith={((metrics.faithfulness ?? 0) * 100).toFixed(0)}%
        {' · '}rel={((metrics.answer_relevance ?? 0) * 100).toFixed(0)}%
        {' · '}hall-risk={((metrics.hallucination_risk ?? 0) * 100).toFixed(0)}%
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

function ToolCallTrace({ toolCalls }) {
  const [open, setOpen] = useState(false);
  if (!toolCalls?.length) return null;
  return (
    <div className="tool-trace">
      <button className="sources-toggle" onClick={() => setOpen(o => !o)}>
        🔧 {open ? 'Hide' : 'Show'} agent tool calls ({toolCalls.length})
      </button>
      {open && (
        <div style={{ marginTop: 8, paddingLeft: 12, borderLeft: '2px solid #334155' }}>
          {toolCalls.map((tc, i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#94a3b8' }}>
                Step {i + 1}: {TOOL_EMOJI[tc.tool] ?? '🔧'}{' '}
                <strong style={{ color: '#60a5fa' }}>{tc.tool}</strong>
              </span>
              <pre style={{
                fontSize: 11, color: '#cbd5e1', background: '#0f172a',
                padding: '6px 10px', borderRadius: 6, marginTop: 4,
                overflowX: 'auto', whiteSpace: 'pre-wrap',
              }}>
                {JSON.stringify(tc.args, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AgentPage() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '🤖 I\'m the **Agentic Research Assistant** — I autonomously pick the right tools to answer your question.\n\nAsk me to compare researchers, find domain experts, or explore specific topics.',
      toolCalls: [],
      sources: [],
      evaluation: null,
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSources, setShowSources] = useState({});
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getHistory = () =>
    messages
      .filter((m, i) => i > 0)
      .slice(-4)
      .map(m => ({ role: m.role, content: m.content }));

  const handleSend = async (text = input) => {
    if (!text.trim() || loading) return;
    const userMsg = { role: 'user', content: text.trim(), toolCalls: [], sources: [], evaluation: null };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const data = await api.agent(text.trim(), getHistory());
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        toolCalls: data.tool_calls || [],
        sources: data.sources || [],
        evaluation: data.evaluation || null,
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Agent error: ${e.message}`,
        toolCalls: [],
        sources: [],
        evaluation: null,
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page chat-page">
      <div className="chat-container">
        {messages.length === 1 && (
          <div className="suggested-questions">
            <p className="sq-label">🔧 Agent-powered queries</p>
            <div className="sq-grid">
              {AGENT_QUESTIONS.map(q => (
                <button key={q} className="sq-btn" onClick={() => handleSend(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}

        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.role}`}>
              <div className="message-avatar">{msg.role === 'user' ? '👤' : '🤖'}</div>
              <div className="message-content-wrapper">
                <div className="message-bubble">
                  <pre className="message-text">{msg.content}</pre>
                </div>

                {/* Tool call trace */}
                {msg.role === 'assistant' && <ToolCallTrace toolCalls={msg.toolCalls} />}

                {/* Eval metrics */}
                {msg.role === 'assistant' && <EvalBadge metrics={msg.evaluation} />}

                {/* Sources */}
                {msg.role === 'assistant' && msg.sources?.length > 0 && (
                  <div className="sources-section">
                    <button className="sources-toggle" onClick={() => setShowSources(p => ({ ...p, [idx]: !p[idx] }))}>
                      📎 {showSources[idx] ? 'Hide' : 'Show'} {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''}
                    </button>
                    {showSources[idx] && (
                      <div className="sources-list">
                        {msg.sources.map((s, si) => <PaperCard key={si} paper={s} rank={si + 1} compact />)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message message-assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-bubble typing-bubble">
                <span style={{ fontSize: 12, color: '#94a3b8' }}>Agent thinking</span>
                <span className="dot" /><span className="dot" /><span className="dot" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input-bar">
          <input
            className="chat-input"
            placeholder="Ask the agent to research, compare, or profile..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            {loading ? <span className="spinner" /> : '↑ Run Agent'}
          </button>
        </div>
      </div>
    </div>
  );
}
