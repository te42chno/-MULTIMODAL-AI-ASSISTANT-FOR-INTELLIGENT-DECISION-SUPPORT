import React, { useState } from 'react';
import { 
  X, 
  Database, 
  Search, 
  FileText, 
  Table2, 
  Image as ImageIcon, 
  Music, 
  Video as VideoIcon, 
  FileCode,
  Layers,
  Calendar
} from 'lucide-react';
import { UploadedFile } from '../../types';

interface KnowledgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  files: UploadedFile[];
}

export const KnowledgeModal: React.FC<KnowledgeModalProps> = ({ isOpen, onClose, files }) => {
  const [search, setSearch] = useState('');

  if (!isOpen) return null;

  const filtered = files.filter((f) =>
    f.filename.toLowerCase().includes(search.toLowerCase()) ||
    (f.summary && f.summary.toLowerCase().includes(search.toLowerCase()))
  );

  const renderIcon = (type: string) => {
    switch (type) {
      case 'document':
        return <FileText className="w-4 h-4 text-rose-400" />;
      case 'dataset':
        return <Table2 className="w-4 h-4 text-cyan-400" />;
      case 'image':
        return <ImageIcon className="w-4 h-4 text-purple-400" />;
      case 'audio':
        return <Music className="w-4 h-4 text-emerald-400" />;
      case 'video':
        return <VideoIcon className="w-4 h-4 text-amber-400" />;
      default:
        return <FileCode className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm select-none">
      <div className="w-full max-w-3xl bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-white tracking-wide">Knowledge Collection Hub</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b border-slate-800/80 bg-slate-900/30">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search indexed knowledge files and summaries..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-xl pl-9 pr-4 py-2 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
            />
          </div>
        </div>

        {/* List of Files */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No files match your query in the active knowledge collection.
            </div>
          ) : (
            filtered.map((file) => (
              <div
                key={file.id}
                className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-colors space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-800">
                      {renderIcon(file.file_type)}
                    </div>
                    <div>
                      <h3 className="text-xs font-semibold text-slate-200">{file.filename}</h3>
                      <p className="text-[10px] text-slate-400">
                        {(file.file_size / 1024).toFixed(1)} KB &bull; Type: {file.file_type.toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
                    <Calendar className="w-3 h-3" />
                    {new Date(file.created_at).toLocaleDateString()}
                  </span>
                </div>

                {file.summary && (
                  <p className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/50 leading-relaxed">
                    {file.summary}
                  </p>
                )}

                {file.metadata && (
                  <div className="flex flex-wrap gap-2 pt-1 text-[10px] text-slate-400">
                    {file.metadata.page_count && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        {file.metadata.page_count} Pages
                      </span>
                    )}
                    {file.metadata.chunk_count && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        {file.metadata.chunk_count} Vector Chunks
                      </span>
                    )}
                    {file.metadata.row_count && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        {file.metadata.row_count} Rows &bull; {file.metadata.column_count} Cols
                      </span>
                    )}
                    {file.metadata.duration_seconds && (
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        Duration: {file.metadata.duration_seconds}s
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
