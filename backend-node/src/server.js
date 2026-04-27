/**
 * AI Researcher Profiling Platform - Node.js Backend
 * Acts as API gateway between React frontend and Python AI service
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
require('dotenv').config();

const searchRouter = require('./routes/search');
const chatRouter = require('./routes/chat');
const clustersRouter = require('./routes/clusters');
const researchersRouter = require('./routes/researchers');
const agentRouter = require('./routes/agent');

const app = express();
const PORT = process.env.PORT || 3001;
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

// ─── Middleware ────────────────────────────────────────────────────────────────
app.use(helmet());
app.use(cors({ origin: process.env.FRONTEND_URL || 'http://localhost:3000' }));
app.use(express.json());
app.use(morgan('dev'));

// ─── Health check ─────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'backend-node', timestamp: new Date().toISOString() });
});

// ─── API Routes ───────────────────────────────────────────────────────────────
app.use('/api/search', searchRouter);
app.use('/api/chat', chatRouter);
app.use('/api/agent', agentRouter);
app.use('/api/clusters', clustersRouter);
app.use('/api/researchers', researchersRouter);

// ─── Error handler ────────────────────────────────────────────────────────────
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error', message: err.message });
});

app.listen(PORT, () => {
  console.log(`\n🚀 Backend API running on http://localhost:${PORT}`);
  console.log(`📡 Proxying AI requests to ${AI_SERVICE_URL}\n`);
});
