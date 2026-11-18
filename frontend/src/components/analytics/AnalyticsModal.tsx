import React from 'react';
import { X, BarChart3, PieChart as PieIcon, ShieldCheck, Database, HardDrive } from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import { UploadedFile } from '../../types';

interface AnalyticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  files: UploadedFile[];
}

const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

export const AnalyticsModal: React.FC<AnalyticsModalProps> = ({ isOpen, onClose, files }) => {
  if (!isOpen) return null;

  // Modality counts
  const modalityCounts: Record<string, number> = {
    document: 0,
    dataset: 0,
    image: 0,
    audio: 0,
    video: 0
  };

  files.forEach((f) => {
    if (modalityCounts[f.file_type] !== undefined) {
      modalityCounts[f.file_type]++;
    }
  });

  const pieData = Object.entries(modalityCounts)
    .filter(([_, count]) => count > 0)
    .map(([modality, count]) => ({
      name: modality.toUpperCase(),
      value: count
    }));

  const totalBytes = files.reduce((acc, f) => acc + f.file_size, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm select-none">
      <div className="w-full max-w-2xl bg-slate-950 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-400" />
            <h2 className="text-sm font-bold text-white tracking-wide">Multimodal Knowledge Analytics</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-[11px] text-slate-400 flex items-center gap-1.5 mb-1">
                <Database className="w-3.5 h-3.5 text-brand-400" /> Total Artifacts
              </span>
              <p className="text-xl font-bold text-white">{files.length}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-[11px] text-slate-400 flex items-center gap-1.5 mb-1">
                <HardDrive className="w-3.5 h-3.5 text-blue-400" /> Storage Ingested
              </span>
              <p className="text-xl font-bold text-white">{(totalBytes / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-[11px] text-slate-400 flex items-center gap-1.5 mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> RAG Grounding
              </span>
              <p className="text-xl font-bold text-emerald-400">Active</p>
            </div>
          </div>

          {/* Chart Distribution */}
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h3 className="text-xs font-semibold text-slate-200">Ingested Modality Distribution</h3>
            {pieData.length === 0 ? (
              <div className="h-56 flex items-center justify-center text-xs text-slate-600">
                Upload evidence to see modality distribution.
              </div>
            ) : (
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={70}
                      label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    >
                      {pieData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
