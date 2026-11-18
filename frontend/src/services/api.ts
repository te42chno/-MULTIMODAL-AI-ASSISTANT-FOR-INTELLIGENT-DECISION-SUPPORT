import axios from 'axios';
import { Conversation, Message, UploadedFile, DecisionReport } from '../types';

// On Vercel the API is served from the same origin via the /api rewrite.
// Local development still targets the standalone FastAPI server on port 8000.
const META_ENV = (import.meta as any).env || {};
const API_BASE_URL =
  META_ENV.VITE_API_URL || (META_ENV.PROD ? '/api' : 'http://127.0.0.1:8000/api');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  // Health
  checkHealth: async () => {
    const res = await apiClient.get('/health');
    return res.data;
  },

  // Conversations
  listConversations: async (): Promise<Conversation[]> => {
    const res = await apiClient.get('/conversations');
    return res.data;
  },

  getConversation: async (id: string): Promise<{ id: string; title: string; messages: Message[] }> => {
    const res = await apiClient.get(`/conversations/${id}`);
    return res.data;
  },

  deleteConversation: async (id: string): Promise<void> => {
    await apiClient.delete(`/conversations/${id}`);
  },

  // Chat
  sendMessage: async (payload: {
    conversation_id?: string;
    message: string;
    modality?: string;
    file_ids?: string[];
    is_decision_support?: boolean;
    system_instruction?: string;
  }): Promise<Message> => {
    const res = await apiClient.post('/chat', payload);
    return res.data;
  },

  // File Uploads
  uploadDocument: async (file: File, conversation_id?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (conversation_id) formData.append('conversation_id', conversation_id);
    const res = await apiClient.post('/upload/document', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  uploadImage: async (file: File, prompt?: string, conversation_id?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (prompt) formData.append('prompt', prompt);
    if (conversation_id) formData.append('conversation_id', conversation_id);
    const res = await apiClient.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  uploadAudio: async (file: File, conversation_id?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (conversation_id) formData.append('conversation_id', conversation_id);
    const res = await apiClient.post('/upload/audio', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  uploadVideo: async (file: File, conversation_id?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (conversation_id) formData.append('conversation_id', conversation_id);
    const res = await apiClient.post('/upload/video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  uploadDataset: async (file: File, conversation_id?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (conversation_id) formData.append('conversation_id', conversation_id);
    const res = await apiClient.post('/upload/dataset', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Files
  listFiles: async (conversation_id?: string): Promise<UploadedFile[]> => {
    const res = await apiClient.get('/conversations/files/list', {
      params: conversation_id ? { conversation_id } : undefined,
    });
    return res.data;
  },

  // Decision Support Direct Request
  generateDecisionReport: async (payload: {
    query: string;
    conversation_id?: string;
    file_ids?: string[];
    criteria?: string[];
  }): Promise<{ report_id: string; conversation_id: string; report: DecisionReport }> => {
    const res = await apiClient.post('/decision-support', payload);
    return res.data;
  },
};
