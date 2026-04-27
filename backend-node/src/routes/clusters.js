/**
 * GET  /api/clusters           — list all domain clusters
 * GET  /api/clusters/:name/researchers — researchers in a cluster
 */

const express = require('express');
const router = express.Router();
const aiClient = require('../aiClient');

router.get('/', async (req, res) => {
  try {
    const { data } = await aiClient.get('/clusters');
    res.json({ success: true, count: data.length, clusters: data });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/:name/researchers', async (req, res) => {
  try {
    const name = req.params.name;
    const { data } = await aiClient.get(`/clusters/${encodeURIComponent(name)}/researchers`);
    res.json({ success: true, cluster: req.params.name, researchers: data });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
