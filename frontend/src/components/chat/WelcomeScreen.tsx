import React from 'react';
import {
  Activity,
  FileText,
  Table2,
  Image as ImageIcon,
  Mic,
  Video,
  Sparkles,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';

interface WelcomeScreenProps {
  onSelectPrompt: (prompt: string, isDecision?: boolean) => void;
}

const suggestions = [
  {
    title: 'Clinical decision brief',
    desc: 'Compare options with evidence, risks and next steps.',
    prompt: 'Generate a clinical decision brief from the uploaded evidence. Compare monitoring, targeted workup and escalation options, and recommend the safest next step.',
    isDecision: true,
    icon: <Sparkles className="w-5 h-5 text-brand-300" />,
    ring: 'from-brand-500/20 to-clinical-500/10',
  },
  {
    title: 'Clinical note RAG',
    desc: 'Ask grounded questions across notes and reports.',
    prompt: 'Summarize the key findings in the uploaded clinical documents with exact source references.',
    isDecision: false,
    icon: <FileText className="w-5 h-5 text-rose-300" />,
    ring: 'from-rose-500/20 to-brand-500/10',
  },
  {
    title: 'Lab table intelligence',
    desc: 'Safe statistics and charts from CSV or Excel data.',
    prompt: 'Analyze the uploaded lab table: report row counts, missing values and the highest and lowest recorded values.',
    isDecision: false,
    icon: <Table2 className="w-5 h-5 text-clinical-300" />,
    ring: 'from-clinical-500/20 to-blue-500/10',
  },
  {
    title: 'Imaging, voice & video',
    desc: 'VLM findings, transcripts and timestamped timelines.',
    prompt: 'Inspect the uploaded media and summarize visible findings, transcribed speech and key timeline events.',
    isDecision: false,
    icon: <ImageIcon className="w-5 h-5 text-purple-300" />,
    ring: 'from-purple-500/20 to-clinical-500/10',
  },
];

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onSelectPrompt }) => {
  return (
    <div className="medical-grid min-h-full flex flex-col items-center justify-center px-6 py-12 max-w-5xl mx-auto select-none fade-in">
      {/* Hero */}
      <div className="relative mb-8">
        <div className="hero-orb w-24 h-24 rounded-[28px]" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Activity className="w-10 h-10 text-white" strokeWidth={1.8} />
        </div>
      </div>

      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-clinical-500/20 bg-clinical-500/[0.07] text-[11px] text-clinical-300 mb-5">
        <span className="w-1.5 h-1.5 rounded-full bg-clinical-400 status-dot" />
        Multimodal evidence workspace
      </div>

      <h1 className="text-3xl md:text-[42px] font-semibold tracking-tight text-center text-white leading-tight">
        Every answer, <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-300 to-clinical-300">grounded in evidence.</span>
      </h1>
      <p className="mt-4 text-sm text-slate-400 text-center max-w-xl leading-relaxed">
        Upload clinical notes, lab tables, images, recordings or video. MedReason indexes every modality into one
        retrieval layer, then answers with traceable citations and structured decision support.
      </p>

      {/* Modality ribbon */}
      <div className="mt-7 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[11px] text-slate-500">
        <span className="flex items-center gap-1.5"><FileText className="w-3.5 h-3.5 text-rose-400" /> Notes</span>
        <span className="flex items-center gap-1.5"><Table2 className="w-3.5 h-3.5 text-clinical-400" /> Labs</span>
        <span className="flex items-center gap-1.5"><ImageIcon className="w-3.5 h-3.5 text-purple-400" /> Imaging</span>
        <span className="flex items-center gap-1.5"><Mic className="w-3.5 h-3.5 text-emerald-400" /> Voice</span>
        <span className="flex items-center gap-1.5"><Video className="w-3.5 h-3.5 text-amber-400" /> Video</span>
      </div>

      {/* Suggestion cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full mt-10">
        {suggestions.map((item) => (
          <button
            key={item.title}
            onClick={() => onSelectPrompt(item.prompt, item.isDecision)}
            className={`card-lift group text-left p-4 rounded-2xl border border-white/[0.07] bg-gradient-to-br ${item.ring} backdrop-blur-xl`}
          >
            <div className="flex items-start justify-between">
              <div className="p-2.5 rounded-xl bg-slate-950/70 border border-white/[0.07]">{item.icon}</div>
              <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-clinical-300 transition-all group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </div>
            <h2 className="mt-3 text-sm font-semibold text-slate-100">{item.title}</h2>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">{item.desc}</p>
          </button>
        ))}
      </div>

      <div className="mt-8 flex items-center gap-2 text-[10px] text-slate-600">
        <ShieldCheck className="w-3.5 h-3.5" />
        Academic demonstration only — not for clinical use.
      </div>
    </div>
  );
};
