/**
 * HTTP client for communicating with the Python FastAPI AI service.
 */

const axios = require('axios');

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

const aiClient = axios.create({
  baseURL: AI_SERVICE_URL,
  timeout: 60000,   // 60s for LLM responses
  headers: { 'Content-Type': 'application/json' },
});

// Log outgoing AI service calls in dev
aiClient.interceptors.request.use((config) => {
  console.log(`[AI Service] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

aiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message;
    console.error(`[AI Service Error] ${msg}`);
    return Promise.reject(new Error(msg));
  }
);

module.exports = aiClient;
