import React from 'react';
import { 
  FileText, 
  Image as ImageIcon, 
  Music, 
  Video as VideoIcon, 
  Table2, 
  ExternalLink, 
  CheckCircle2, 
  Layers, 
  Cpu, 
  X,
  FileCode,
  ShieldCheck
} from 'lucide-react';
import { UploadedFile, Citation } from '../../types';

interface RightDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeFiles: UploadedFile[];
  activeCitations: Citation[];
  modelInfo: {
    provider: string;
    model: string;
    visionProvider?: string;
    embeddingProvider?: string;
    speechProvider?: string;
    groundedStatus: boolean;
  };
}

export const RightDrawer: React.FC<RightDrawerProps> = ({
  isOpen,
  onClose,
  activeFiles,
  activeCitations,
  modelInfo,
}) => {
  if (!isOpen) return null;

  const renderFileIcon = (type: string) => {
    switch (type) {
      case 'document':
        return <FileText className="w-4 h-4 text-rose-400" />;
      case 'image':
        return <ImageIcon className="w-4 h-4 text-purple-400" />;
      case 'audio':
        return <Music className="w-4 h-4 text-emerald-400" />;
      case 'video':
        return <VideoIcon className="w-4 h-4 text-amber-400" />;
      case 'dataset':
        return <Table2 className="w-4 h-4 text-cyan-400" />;
      default:
        return <FileCode className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <aside className="w-[336px] h-screen bg-slate-950/85 border-l border-white/[0.07] flex flex-col z-30 transition-all duration-300 backdrop-blur-xl">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-brand-400" />
          <h2 className="text-xs font-semibold text-white tracking-[0.14em] uppercase">Evidence Inspector</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Model Status Card */}
        <div className="glass-card p-3.5 rounded-2xl space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-clinical-400" /> Model pipeline
            </span>
            <span className="bg-clinical-500/10 text-clinical-300 font-mono text-[10px] px-2 py-0.5 rounded border border-clinical-500/20">
              {modelInfo.provider.toUpperCase()}
            </span>
          </div>
          <div className="text-xs text-slate-200 font-medium truncate font-mono">{modelInfo.model}</div>
          <div className="grid grid-cols-2 gap-1.5 pt-1 text-[10px]">
            <div className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className="text-slate-500 block">VLM</span>
              <span className="text-purple-300">{modelInfo.visionProvider || '—'}</span>
            </div>
            <div className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <span className="text-slate-500 block">Embeddings</span>
              <span className="text-brand-300">{modelInfo.embeddingProvider || '—'}</span>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-clinical-400 pt-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Hybrid retrieval + citation validation</span>
          </div>
        </div>

        {/* Retrieved Citations */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Grounded Sources ({activeCitations.length})
            </h3>
          </div>

          {activeCitations.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/50 text-center text-slate-500 text-xs">
              No active citations retrieved for this message.
            </div>
          ) : (
            <div className="space-y-2.5">
              {activeCitations.map((citation, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-brand-500/40 transition-colors text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between text-slate-300 font-medium">
                    <span className="truncate max-w-[170px] text-brand-300">{citation.filename}</span>
                    {(citation.row_or_item || citation.page_number) && (
                      <span className="text-[10px] text-slate-400 bg-white/[0.06] px-1.5 py-0.5 rounded">
                        {citation.row_or_item || `p. ${citation.page_number}`}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-400 text-[11px] leading-relaxed line-clamp-3 italic">
                    "{citation.snippet}"
                  </p>
                  {citation.relevance_score !== undefined && (
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
                      <span>Cosine Match:</span>
                      <span className="text-emerald-400 font-mono">
                        {(citation.relevance_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Attached Files List */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h3 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Uploaded Artifacts ({activeFiles.length})
            </h3>
          </div>

          {activeFiles.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/50 text-center text-slate-500 text-xs">
              No files uploaded in current context.
            </div>
          ) : (
            <div className="space-y-2">
              {activeFiles.map((file) => (
                <div
                  key={file.id}
                  className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2 truncate">
                    {renderFileIcon(file.file_type)}
                    <div className="truncate">
                      <p className="text-slate-200 truncate font-medium">{file.filename}</p>
                      <p className="text-[10px] text-slate-500">
                        {(file.file_size / 1024).toFixed(1)} KB &bull; {file.file_type}
                      </p>
                    </div>
                  </div>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-2 flex items-start gap-2 text-[10px] leading-relaxed text-slate-600">
          <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          Academic demonstration only. Do not upload real patient data.
        </div>
      </div>
    </aside>
  );
};
