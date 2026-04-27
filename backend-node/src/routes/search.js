/**
 * POST /api/search
 * Semantic search over researcher publications via FAISS.
 */

const express = require('express');
const router = express.Router();
const aiClient = require('../aiClient');

router.post('/', async (req, res) => {
  try {
    const { query, top_k = 5, cluster_filter, min_citations } = req.body;

    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({ error: 'query is required and must be a non-empty string' });
    }

    const payload = { query: query.trim(), top_k };
    if (cluster_filter) payload.cluster_filter = cluster_filter;
    if (min_citations !== undefined) payload.min_citations = min_citations;

    const { data } = await aiClient.post('/search', payload);

    res.json({
      success: true,
      query: query.trim(),
      count: data.length,
      results: data,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
