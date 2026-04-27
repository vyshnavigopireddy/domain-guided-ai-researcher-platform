/**
 * POST /api/agent
 * LangGraph multi-step agentic Q&A.
 * The agent autonomously selects tools (search, researcher profile, cluster)
 * and returns a grounded answer with tool call trace + eval metrics.
 */

const express = require('express');
const router = express.Router();
const aiClient = require('../aiClient');

router.post('/', async (req, res) => {
  try {
    const { query, chat_history = [] } = req.body;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({ error: 'query is required' });
    }

    const { data } = await aiClient.post('/agent', {
      query: query.trim(),
      chat_history,
    });

    res.json({
      success: true,
      answer: data.answer,
      tool_calls: data.tool_calls,
      sources: data.sources,
      query: data.query,
      evaluation: data.evaluation,   // RAGAS metrics
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
