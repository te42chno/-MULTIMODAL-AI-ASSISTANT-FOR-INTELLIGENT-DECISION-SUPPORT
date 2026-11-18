import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Bot, 
  User, 
  Copy, 
  Check, 
  RotateCcw, 
  Volume2, 
  VolumeX,
  FileText, 
  Table2, 
  Sparkles,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  Lightbulb
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import { Message, ChartSpec } from '../../types';
import { DecisionReportView } from './DecisionReportView';

interface ChatMessageProps {
  message: Message;
  onRegenerate?: () => void;
  onSelectCitation?: (sourceId: string) => void;
}

const COLORS = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onRegenerate,
  onSelectCitation,
}) => {
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const isAssistant = message.role === 'assistant';

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeak = () => {
    if ('speechSynthesis' in window) {
      if (speaking) {
        window.speechSynthesis.cancel();
        setSpeaking(false);
      } else {
        const cleanText = message.content.replace(/[#*`_\[\]()]/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.0;
        utterance.onend = () => setSpeaking(false);
        utterance.onerror = () => setSpeaking(false);
        window.speechSynthesis.speak(utterance);
        setSpeaking(true);
      }
    }
  };

  const renderChart = (chart: ChartSpec) => {
    return (
      <div className="my-4 p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
          <span className="flex items-center gap-1.5">
            <TrendingUp className="w-4 h-4 text-brand-400" />
            {chart.title}
          </span>
          <span className="text-[10px] uppercase text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
            {chart.chart_type} Chart
          </span>
        </div>
        <p className="text-[11px] text-slate-400">{chart.description}</p>

        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            {chart.chart_type === 'bar' ? (
              <BarChart data={chart.data} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            ) : chart.chart_type === 'line' ? (
              <LineChart data={chart.data} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="x" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                <Line type="monotone" dataKey="y" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#8b5cf6', r: 3 }} />
              </LineChart>
            ) : (
              <PieChart>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#f8fafc' }} />
                <Pie data={chart.data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} fill="#8884d8">
                  {chart.data.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  return (
    <div className={`py-5 px-4 md:px-8 flex gap-4 ${isAssistant ? 'bg-slate-900/30' : 'bg-transparent'}`}>
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isAssistant ? (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-blue-500 flex items-center justify-center shadow-md shadow-brand-500/20">
            <Bot className="w-4 h-4 text-white" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center">
            <User className="w-4 h-4 text-slate-300" />
          </div>
        )}
      </div>

      {/* Message Body */}
      <div className="flex-1 space-y-3 min-w-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-200">
              {isAssistant ? 'MedReason' : 'You'}
            </span>
            {message.modality !== 'text' && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/20 uppercase">
                {message.modality}
              </span>
            )}
          </div>
          <span className="text-[11px] text-slate-500">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Structured report replaces raw markdown when available */}
        {message.metadata?.report ? (
          <DecisionReportView report={message.metadata.report} />
        ) : (
          <div className="prose-dark text-xs md:text-sm leading-relaxed overflow-hidden">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Embedded Chart if present */}
        {message.metadata?.chart && renderChart(message.metadata.chart)}

        {/* Embedded Data Table Preview if present */}
        {message.metadata?.data_table && message.metadata.data_table.length > 0 && (
          <div className="my-3 overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60 p-2">
            <table className="w-full text-left text-xs text-slate-300">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] text-slate-400">
                  {Object.keys(message.metadata.data_table[0]).map((k) => (
                    <th key={k} className="p-2 font-medium">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.metadata.data_table.map((row, i) => (
                  <tr key={i} className="border-b border-slate-800/40 hover:bg-slate-800/30">
                    {Object.values(row).map((val: any, j) => (
                      <td key={j} className="p-2 font-mono text-[11px] text-slate-300">{String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Citations Badges */}
        {message.sources && message.sources.length > 0 && (
          <div className="pt-2 flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Sources:
            </span>
            {message.sources.map((src, i) => (
              <button
                key={i}
                onClick={() => onSelectCitation && onSelectCitation(src.source_id)}
                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 text-[11px] text-brand-300 transition-colors"
                title={`Relevance: ${src.relevance_score ? (src.relevance_score * 100).toFixed(0) + '%' : 'Verified'}\n\n"${src.snippet}"`}
              >
                <FileText className="w-3 h-3 text-slate-400" />
                <span className="truncate max-w-[130px]">{src.filename}</span>
                {(src.row_or_item || src.page_number) && (
                  <span className="text-slate-500 font-mono">
                    {src.row_or_item || `p.${src.page_number}`}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        {/* Assistant Footer Actions (Copy, TTS, Regenerate) */}
        {isAssistant && (
          <div className="flex items-center gap-2 pt-2 text-slate-400">
            <button
              onClick={handleCopy}
              className="p-1.5 hover:text-white hover:bg-slate-800 rounded-lg text-xs flex items-center gap-1 transition-colors"
              title="Copy response"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
            </button>

            <button
              onClick={handleSpeak}
              className={`p-1.5 hover:text-white hover:bg-slate-800 rounded-lg text-xs flex items-center gap-1 transition-colors ${
                speaking ? 'text-brand-400 bg-brand-500/10' : ''
              }`}
              title="Read aloud"
            >
              {speaking ? <VolumeX className="w-3.5 h-3.5 text-brand-400 animate-pulse" /> : <Volume2 className="w-3.5 h-3.5" />}
              <span className="text-[11px]">{speaking ? 'Stop' : 'Listen'}</span>
            </button>

            {onRegenerate && (
              <button
                onClick={onRegenerate}
                className="p-1.5 hover:text-white hover:bg-slate-800 rounded-lg text-xs flex items-center gap-1 transition-colors"
                title="Regenerate response"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span className="text-[11px]">Regenerate</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
