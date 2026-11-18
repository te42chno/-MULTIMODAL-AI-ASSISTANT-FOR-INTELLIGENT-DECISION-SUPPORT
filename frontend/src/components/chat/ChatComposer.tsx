import React, { useState, useRef, useEffect } from 'react';
import { 
  Paperclip, 
  Send, 
  Mic, 
  MicOff, 
  FileText, 
  Image as ImageIcon, 
  Table2, 
  Video as VideoIcon, 
  Sparkles, 
  X,
  Loader2,
  CheckCircle2,
  FileCode,
  Music
} from 'lucide-react';
import { UploadedFile } from '../../types';

interface ChatComposerProps {
  onSendMessage: (message: string, isDecisionSupport: boolean, fileIds: string[]) => void;
  onFileUpload: (file: File) => Promise<UploadedFile | null>;
  isProcessing: boolean;
  activeFiles: UploadedFile[];
  onRemoveFile: (fileId: string) => void;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSendMessage,
  onFileUpload,
  isProcessing,
  activeFiles,
  onRemoveFile,
}) => {
  const [input, setInput] = useState('');
  const [isDecisionSupport, setIsDecisionSupport] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [uploading, setUploading] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  // Voice recording logic
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioFile = new File([audioBlob], `mic_recording_${Date.now()}.webm`, { type: 'audio/webm' });
        stream.getTracks().forEach((track) => track.stop());
        
        // Upload audio file and attach
        setUploading(true);
        const uploaded = await onFileUpload(audioFile);
        setUploading(false);
        if (uploaded && uploaded.summary) {
          setInput((prev) => (prev ? `${prev}\n\n[Transcribed Audio: ${uploaded.summary}]` : `Please analyze this transcribed question: ${uploaded.summary}`));
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      alert('Microphone permission denied or audio device not found.');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if ((!input.trim() && activeFiles.length === 0) || isProcessing) return;
    const currentInput = input.trim() || 'Please analyze the attached files and provide grounded insights.';
    onSendMessage(
      currentInput,
      isDecisionSupport,
      activeFiles.map((f) => f.id)
    );
    setInput('');
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    setUploading(true);
    for (let i = 0; i < files.length; i++) {
      await onFileUpload(files[i]);
    }
    setUploading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const renderFileBadge = (type: string) => {
    switch (type) {
      case 'document':
        return <FileText className="w-3 h-3 text-rose-400" />;
      case 'image':
        return <ImageIcon className="w-3 h-3 text-purple-400" />;
      case 'dataset':
        return <Table2 className="w-3 h-3 text-cyan-400" />;
      case 'video':
        return <VideoIcon className="w-3 h-3 text-amber-400" />;
      case 'audio':
        return <Music className="w-3 h-3 text-emerald-400" />;
      default:
        return <FileCode className="w-3 h-3 text-slate-400" />;
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4 select-none">
      <div className="glass-panel rounded-2xl p-3 border border-slate-800 shadow-2xl space-y-2">
        {/* Active Attached Files Carousel / Badges */}
        {activeFiles.length > 0 && (
          <div className="flex flex-wrap gap-2 pb-2 border-b border-slate-800/60">
            {activeFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300"
              >
                {renderFileBadge(file.file_type)}
                <span className="truncate max-w-[150px] font-medium">{file.filename}</span>
                <button
                  onClick={() => onRemoveFile(file.id)}
                  className="p-0.5 hover:text-rose-400 text-slate-500 rounded"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Recording status banner */}
        {isRecording && (
          <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs animate-pulse">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span>Recording microphone input: {recordingSeconds}s</span>
            </div>
            <button
              onClick={stopRecording}
              className="text-xs font-semibold underline hover:text-white"
            >
              Finish & Attach
            </button>
          </div>
        )}

        {/* Input Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isDecisionSupport
              ? "Ask for a clinical decision brief from the uploaded evidence..."
              : "Ask about a clinical note, lab table, image, recording or video (Enter to send)..."
          }
          rows={1}
          disabled={isProcessing}
          className="w-full bg-transparent text-slate-200 placeholder-slate-500 text-xs md:text-sm resize-none focus:outline-none p-1 leading-relaxed"
        />

        {/* Bottom Toolbar Controls */}
        <div className="flex items-center justify-between pt-1">
          {/* Left Actions: Attach, Voice, Decision Toggle */}
          <div className="flex items-center gap-1.5">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              multiple
              accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls,.png,.jpg,.jpeg,.webp,.mp4,.mov,.avi,.wav,.mp3,.webm,.m4a"
              className="hidden"
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isProcessing || uploading}
              className="p-2 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-xl text-xs flex items-center gap-1 transition-colors"
              title="Attach Document, Dataset, Image, Audio, or Video"
            >
              {uploading ? (
                <Loader2 className="w-4 h-4 text-brand-400 animate-spin" />
              ) : (
                <Paperclip className="w-4 h-4" />
              )}
              <span className="hidden sm:inline text-xs font-medium">Attach</span>
            </button>

            {/* Microphone Audio Recording Button */}
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing || uploading}
              className={`p-2 rounded-xl text-xs flex items-center gap-1 transition-all ${
                isRecording
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
              title={isRecording ? "Stop recording" : "Record voice query"}
            >
              {isRecording ? <MicOff className="w-4 h-4 text-rose-400" /> : <Mic className="w-4 h-4" />}
              <span className="hidden sm:inline text-xs font-medium">
                {isRecording ? 'Stop' : 'Voice'}
              </span>
            </button>

            {/* Decision Support Toggle Pill */}
            <button
              onClick={() => setIsDecisionSupport(!isDecisionSupport)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                isDecisionSupport
                  ? 'bg-brand-600/20 text-brand-300 border-brand-500/50 shadow-sm shadow-brand-500/20'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700'
              }`}
              title="Generate a structured clinical decision brief with evidence, options and risks"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isDecisionSupport ? 'text-clinical-300' : 'text-slate-500'}`} />
              <span>Decision Brief</span>
            </button>
          </div>

          {/* Right Action: Send Button */}
          <button
            onClick={handleSend}
            disabled={(!input.trim() && activeFiles.length === 0) || isProcessing}
            className={`flex items-center justify-center p-2.5 rounded-xl text-white transition-all ${
              (!input.trim() && activeFiles.length === 0) || isProcessing
                ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                : 'bg-gradient-to-r from-brand-600 to-clinical-600 hover:from-brand-500 hover:to-clinical-500 shadow-lg shadow-brand-600/25 active:scale-95'
            }`}
          >
            {isProcessing ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Supported format legend */}
      <div className="flex items-center justify-center gap-4 pt-2 text-[11px] text-slate-500">
        <span>Notes &bull; PDF &bull; DOCX</span>
        <span>Labs &bull; CSV &bull; Excel</span>
        <span>Imaging &bull; PNG/JPG</span>
        <span>Voice &bull; Video</span>
      </div>
    </div>
  );
};
