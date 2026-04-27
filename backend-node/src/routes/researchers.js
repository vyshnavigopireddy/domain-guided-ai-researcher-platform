/**
 * GET /api/researchers/:name   — researcher profile
 */

const express = require('express');
const router = express.Router();
const aiClient = require('../aiClient');

router.get('/:name', async (req, res) => {
  try {
    const name = req.params.name;
    const { data } = await aiClient.get(`/researchers/${encodeURIComponent(name)}`);
    res.json({ success: true, profile: data });
  } catch (err) {
    if (err.message.includes('404') || err.message.includes('not found')) {
      return res.status(404).json({ error: `Researcher '${req.params.name}' not found` });
    }
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
