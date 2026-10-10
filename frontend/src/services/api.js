import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

export const runAudit = async (payload) => {
  const response = await apiClient.post('/audit', payload);
  return response.data;
};

export const getSampleData = async () => {
  const response = await apiClient.get('/sample');
  return response.data;
};

export const getHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};
