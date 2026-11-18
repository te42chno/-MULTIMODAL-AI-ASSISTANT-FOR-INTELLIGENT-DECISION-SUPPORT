import React from 'react';
import { X, Settings as SettingsIcon, Cpu, KeyRound, Info, ShieldCheck } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentProvider: string;
  currentModel: string;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  currentProvider,
  currentModel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm select-none">
      <div className="w-full max-w-lg bg-slate-950 border border-white/[0.08] rounded-2xl shadow-2xl overflow-hidden">
        <div className="p-4 border-b border-white/[0.07] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-slate-400" />
            <h2 className="text-sm font-semibold text-white">Runtime configuration</h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-500 hover:text-white rounded-lg hover:bg-white/5">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          <div className="p-3.5 rounded-xl bg-brand-500/[0.08] border border-brand-500/20 text-xs text-brand-200 flex items-start gap-2.5">
            <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-brand-300" />
            <span>
              Providers are configured in <code className="px-1 rounded bg-black/30">backend/.env</code>. Restart the
              backend after changing keys. Free options: Groq for fast text generation and Gemini for vision.
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
              <p className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-clinical-400" /> Text provider
              </p>
              <p className="mt-1.5 text-sm font-medium text-white">{currentProvider}</p>
            </div>
            <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
              <p className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-brand-400" /> Active model
              </p>
              <p className="mt-1.5 text-xs font-mono text-brand-200 truncate">{currentModel}</p>
            </div>
          </div>

          <div className="pt-2 border-t border-white/[0.07]">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Installed services
            </p>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              {[
                ['Hybrid RAG', 'Hashing + lexical'],
                ['Vision', 'Gemini / OpenCV'],
                ['Speech', 'Whisper / local'],
                ['Analytics', 'Pandas planner'],
              ].map(([label, value]) => (
                <div key={label} className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-between">
                  <span className="text-slate-400">{label}</span>
                  <span className="text-clinical-300 font-mono text-[10px]">{value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-start gap-2 text-[10px] leading-relaxed text-slate-600">
            <ShieldCheck className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
            Academic demonstration only — not for clinical use.
          </div>
        </div>

        <div className="p-4 border-t border-white/[0.07] flex justify-end bg-white/[0.02]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-white bg-brand-600 hover:bg-brand-500 rounded-xl transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
