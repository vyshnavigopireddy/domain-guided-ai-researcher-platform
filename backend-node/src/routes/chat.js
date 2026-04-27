/**
 * POST /api/chat
 * RAG-based conversational Q&A backed by FAISS + LLM.
 */

const express = require('express');
const router = express.Router();
const aiClient = require('../aiClient');

router.post('/', async (req, res) => {
  try {
    const { query, top_k = 5, chat_history = [] } = req.body;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({ error: 'query is required' });
    }

    const { data } = await aiClient.post('/chat', {
      query: query.trim(),
      top_k,
      chat_history,
    });

    res.json({
      success: true,
      answer: data.answer,
      sources: data.sources,
      query: data.query,
      evaluation: data.evaluation || null,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
