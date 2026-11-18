import React, { useState, useEffect, useRef } from 'react';
import { 
  Sidebar 
} from './components/layout/Sidebar';
import { 
  RightDrawer 
} from './components/layout/RightDrawer';
import { 
  ChatMessage 
} from './components/chat/ChatMessage';
import { 
  ChatComposer 
} from './components/chat/ChatComposer';
import { 
  WelcomeScreen 
} from './components/chat/WelcomeScreen';
import { 
  AnalyticsModal 
} from './components/analytics/AnalyticsModal';
import { 
  KnowledgeModal 
} from './components/knowledge/KnowledgeModal';
import { 
  SettingsModal 
} from './components/settings/SettingsModal';
import { 
  apiService 
} from './services/api';
import { 
  Conversation, 
  Message, 
  UploadedFile, 
  Citation 
} from './types';
import {
  Activity,
  Layers,
  Bot,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';

export const App: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeFiles, setActiveFiles] = useState<UploadedFile[]>([]);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [rightDrawerOpen, setRightDrawerOpen] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modals state
  const [knowledgeOpen, setKnowledgeOpen] = useState(false);
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Model info state
  const [modelInfo, setModelInfo] = useState({
    provider: 'Mock',
    model: 'grounded-fallback',
    visionProvider: 'mock',
    embeddingProvider: 'hashing_cosine',
    speechProvider: 'local',
    groundedStatus: true
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  // Load conversations and health on mount
  useEffect(() => {
    loadConversations();
    checkSystemHealth();
  }, []);

  const checkSystemHealth = async () => {
    try {
      const health = await apiService.checkHealth();
      setModelInfo({
        provider: health.llm_provider || 'mock',
        model: health.llm_provider === 'mock' ? 'grounded-fallback' : (health.llm_model || 'configured-model'),
        visionProvider: health.vision_provider || 'mock',
        embeddingProvider: health.embedding_provider || 'hashing_cosine',
        speechProvider: health.speech_provider || 'local',
        groundedStatus: true
      });
    } catch (e) {
      console.warn('Backend server connecting...');
    }
  };

  const loadConversations = async () => {
    try {
      const data = await apiService.listConversations();
      setConversations(data);
    } catch (err: any) {
      console.error('Error fetching conversations:', err);
    }
  };

  const handleSelectConversation = async (id: string) => {
    try {
      setActiveConversationId(id);
      setIsProcessing(true);
      const data = await apiService.getConversation(id);
      setMessages(data.messages || []);
      
      // Update citations from latest message
      const latestAssistant = [...(data.messages || [])].reverse().find((m) => m.role === 'assistant');
      if (latestAssistant && latestAssistant.sources) {
        setActiveCitations(latestAssistant.sources);
      } else {
        setActiveCitations([]);
      }
      setIsProcessing(false);
    } catch (err: any) {
      setIsProcessing(false);
      setErrorMessage('Could not load conversation history.');
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(undefined);
    setMessages([]);
    setActiveFiles([]);
    setActiveCitations([]);
    setErrorMessage(null);
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await apiService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        handleNewChat();
      }
    } catch (err) {
      setErrorMessage('Failed to delete conversation.');
    }
  };

  const handleFileUpload = async (file: File): Promise<UploadedFile | null> => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    try {
      let uploaded: any = null;
      if (['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
        uploaded = await apiService.uploadDocument(file, activeConversationId);
      } else if (['csv', 'xlsx', 'xls'].includes(ext)) {
        uploaded = await apiService.uploadDataset(file, activeConversationId);
      } else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
        uploaded = await apiService.uploadImage(file, undefined, activeConversationId);
      } else if (['mp4', 'mov', 'avi'].includes(ext)) {
        uploaded = await apiService.uploadVideo(file, activeConversationId);
      } else if (['mp3', 'wav', 'webm', 'm4a'].includes(ext)) {
        uploaded = await apiService.uploadAudio(file, activeConversationId);
      } else {
        throw new Error(`File type .${ext} is not supported.`);
      }

      const fileObj: UploadedFile = {
        id: uploaded.file_id,
        filename: uploaded.filename,
        file_type: ['csv', 'xlsx', 'xls'].includes(ext)
          ? 'dataset'
          : ['png', 'jpg', 'jpeg', 'webp'].includes(ext)
          ? 'image'
          : ['mp4', 'mov', 'avi'].includes(ext)
          ? 'video'
          : ['mp3', 'wav', 'webm', 'm4a'].includes(ext)
          ? 'audio'
          : 'document',
        file_size: uploaded.file_size,
        summary: uploaded.summary || uploaded.transcription,
        metadata: uploaded,
        created_at: new Date().toISOString()
      };

      setActiveFiles((prev) => [...prev, fileObj]);
      return fileObj;
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || err.message || 'File upload failed.');
      return null;
    }
  };

  const handleRemoveFile = (fileId: string) => {
    setActiveFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleSendMessage = async (
    messageText: string,
    isDecisionSupport: boolean,
    fileIds: string[]
  ) => {
    setErrorMessage(null);
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId || '',
      role: 'user',
      content: messageText,
      modality: isDecisionSupport ? 'decision' : (activeFiles.length > 0 ? activeFiles[0].file_type : 'text'),
      file_ids: fileIds,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMessage]);
    setIsProcessing(true);

    try {
      const response = await apiService.sendMessage({
        conversation_id: activeConversationId,
        message: messageText,
        modality: tempUserMessage.modality,
        file_ids: fileIds,
        is_decision_support: isDecisionSupport
      });

      // Update state with server response
      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id);
        loadConversations();
      }

      setMessages((prev) => [...prev, response]);
      if (response.sources && response.sources.length > 0) {
        setActiveCitations(response.sources);
      }
      setIsProcessing(false);
    } catch (err: any) {
      setIsProcessing(false);
      setErrorMessage(err.response?.data?.detail || err.message || 'Error processing request.');
    }
  };

  return (
    <div className="app-shell flex h-screen w-screen overflow-hidden font-sans text-slate-100">
      {/* Left Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onOpenKnowledge={() => setKnowledgeOpen(true)}
        onOpenAnalytics={() => setAnalyticsOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col h-screen min-w-0 relative">
        {/* Top Navbar */}
        <header className="h-14 border-b border-white/[0.06] px-5 flex items-center justify-between bg-slate-950/60 backdrop-blur-xl z-20">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.07] flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-clinical-400" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xs font-semibold text-slate-200 truncate max-w-xs md:max-w-md">
                {activeConversationId
                  ? conversations.find((c) => c.id === activeConversationId)?.title || 'Active case'
                  : 'New clinical case'}
              </h2>
              <p className="text-[10px] text-slate-500">Evidence-grounded workspace</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-rose-500/[0.08] border border-rose-500/20 text-[10px] text-rose-300">
              <ShieldCheck className="w-3 h-3" />
              Academic use only
            </div>
            <button
              onClick={() => setRightDrawerOpen(!rightDrawerOpen)}
              className={`p-2 rounded-xl text-xs flex items-center gap-1.5 transition-all ${
                rightDrawerOpen
                  ? 'bg-clinical-500/10 text-clinical-300 border border-clinical-500/30'
                  : 'text-slate-400 hover:bg-white/[0.05] border border-transparent'
              }`}
              title="Toggle evidence inspector"
            >
              <Layers className="w-4 h-4" />
              <span className="hidden md:inline text-xs font-medium">Evidence</span>
            </button>
          </div>
        </header>

        {/* Error notification banner */}
        {errorMessage && (
          <div className="mx-4 mt-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs underline hover:text-white"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Chat message viewport / Welcome screen */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <WelcomeScreen
              onSelectPrompt={(prompt, isDecision) =>
                handleSendMessage(prompt, isDecision || false, activeFiles.map((f) => f.id))
              }
            />
          ) : (
            <div className="max-w-4xl mx-auto divide-y divide-slate-800/40">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onRegenerate={() => {
                    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
                    if (lastUser) {
                      handleSendMessage(lastUser.content, lastUser.modality === 'decision', lastUser.file_ids || []);
                    }
                  }}
                  onSelectCitation={() => setRightDrawerOpen(true)}
                />
              ))}

              {isProcessing && (
                <div className="py-6 px-4 md:px-8 flex gap-4 bg-slate-900/20">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-500 flex items-center justify-center shadow-md">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                      <span>Retrieving multimodal evidence</span>
                      <span className="flex space-x-1">
                        <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                        <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                        <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce"></span>
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Hybrid search across notes, labs, imaging and transcripts. Validating citations...
                    </p>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Composer Toolbar */}
        <ChatComposer
          onSendMessage={handleSendMessage}
          onFileUpload={handleFileUpload}
          isProcessing={isProcessing}
          activeFiles={activeFiles}
          onRemoveFile={handleRemoveFile}
        />
      </main>

      {/* Right Drawer */}
      <RightDrawer
        isOpen={rightDrawerOpen}
        onClose={() => setRightDrawerOpen(false)}
        activeFiles={activeFiles}
        activeCitations={activeCitations}
        modelInfo={modelInfo}
      />

      {/* Modals */}
      <KnowledgeModal
        isOpen={knowledgeOpen}
        onClose={() => setKnowledgeOpen(false)}
        files={activeFiles}
      />

      <AnalyticsModal
        isOpen={analyticsOpen}
        onClose={() => setAnalyticsOpen(false)}
        files={activeFiles}
      />

      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        currentProvider={modelInfo.provider}
        currentModel={modelInfo.model}
      />
    </div>
  );
};

export default App;
