import React from 'react';
import {
  ClipboardList,
  FlaskConical,
  GitBranch,
  ShieldAlert,
  ArrowRight,
  CheckCircle2,
  Info,
  Quote,
} from 'lucide-react';
import { DecisionReport } from '../../types';

interface Props {
  report: DecisionReport;
}

const severityColor: Record<string, string> = {
  Low: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20',
  Medium: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
  High: 'text-rose-300 bg-rose-500/10 border-rose-500/20',
  Critical: 'text-rose-200 bg-rose-600/15 border-rose-500/30',
};

export const DecisionReportView: React.FC<Props> = ({ report }) => {
  return (
    <div className="my-4 rounded-2xl border border-white/[0.08] bg-slate-950/70 backdrop-blur-xl overflow-hidden fade-in">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/[0.07] bg-gradient-to-r from-brand-500/10 to-clinical-500/[0.07]">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-clinical-300">
          <ClipboardList className="w-3.5 h-3.5" />
          Structured clinical decision brief
        </div>
        <h3 className="mt-1.5 text-base font-semibold text-white">{report.title}</h3>
        <p className="mt-1 text-xs text-slate-400">Objective: {report.objective}</p>
      </div>

      <div className="p-5 space-y-6">
        {/* Executive summary */}
        <Section icon={<Quote className="w-3.5 h-3.5 text-brand-300" />} title="Executive summary">
          <p className="text-xs leading-relaxed text-slate-300">{report.executive_summary}</p>
        </Section>

        {/* Findings */}
        <Section icon={<FlaskConical className="w-3.5 h-3.5 text-clinical-300" />} title="Key findings">
          <ul className="space-y-1.5">
            {report.key_findings.map((finding, i) => (
              <li key={i} className="flex gap-2 text-xs text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-clinical-400 mt-1.5 flex-shrink-0" />
                {finding}
              </li>
            ))}
          </ul>
          {report.quantitative_metrics && Object.keys(report.quantitative_metrics).length > 0 && (
            <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-2">
              {Object.entries(report.quantitative_metrics).map(([key, value]) => (
                <div key={key} className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <p className="text-[10px] text-slate-500 truncate">{key}</p>
                  <p className="text-xs font-mono text-clinical-300 mt-0.5">{String(value)}</p>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Alternatives */}
        <Section icon={<GitBranch className="w-3.5 h-3.5 text-purple-300" />} title="Options & trade-offs">
          <div className="grid gap-2.5">
            {report.alternatives.map((alt, i) => (
              <div key={i} className="p-3.5 rounded-xl bg-white/[0.025] border border-white/[0.07] card-lift">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-xs font-semibold text-white">{alt.name}</h4>
                  <div className="flex items-center gap-1.5">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] border ${severityColor[alt.risk_level] || severityColor.Medium}`}>
                      {alt.risk_level} risk
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] border border-brand-500/20 bg-brand-500/10 text-brand-200 font-mono">
                      {alt.feasibility_score}/10
                    </span>
                  </div>
                </div>
                <p className="mt-1.5 text-[11px] text-slate-400">{alt.description}</p>
                <div className="mt-2.5 grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-emerald-400 font-medium">Pros: </span>
                    <span className="text-slate-400">{alt.pros.join(' · ')}</span>
                  </div>
                  <div>
                    <span className="text-rose-400 font-medium">Cons: </span>
                    <span className="text-slate-400">{alt.cons.join(' · ')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Risks */}
        <Section icon={<ShieldAlert className="w-3.5 h-3.5 text-rose-300" />} title="Risks, limitations & mitigations">
          <div className="space-y-2">
            {report.risks_and_limitations.map((risk, i) => (
              <div key={i} className="flex gap-2.5 p-2.5 rounded-xl bg-white/[0.025] border border-white/[0.06]">
                <span className={`px-2 py-0.5 h-fit rounded text-[10px] border ${severityColor[risk.severity] || severityColor.Medium}`}>
                  {risk.severity}
                </span>
                <div>
                  <p className="text-xs font-medium text-slate-200">{risk.risk}</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">{risk.mitigation_strategy}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Recommendation */}
        <div className="p-4 rounded-xl border border-clinical-500/20 bg-clinical-500/[0.07]">
          <div className="flex items-center gap-2 text-[11px] font-semibold text-clinical-300 mb-1.5">
            <CheckCircle2 className="w-4 h-4" />
            Recommended path
          </div>
          <p className="text-xs leading-relaxed text-slate-200">{report.final_recommendation}</p>
        </div>

        {/* Next steps */}
        <Section icon={<ArrowRight className="w-3.5 h-3.5 text-brand-300" />} title="Actionable next steps">
          <ol className="space-y-1.5">
            {report.actionable_next_steps.map((step, i) => (
              <li key={i} className="flex items-start gap-2.5 text-xs text-slate-300">
                <span className="w-5 h-5 rounded-lg bg-brand-500/10 border border-brand-500/20 text-brand-300 text-[10px] flex items-center justify-center flex-shrink-0">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </Section>

        {/* Evidence */}
        {report.evidence_sources.length > 0 && (
          <div className="pt-3 border-t border-white/[0.06] flex flex-wrap items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" /> Evidence:
            </span>
            {report.evidence_sources.slice(0, 6).map((src, i) => (
              <span key={i} className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.07] text-[10px] text-clinical-300">
                [E{i + 1}] {src.filename} {src.row_or_item || (src.page_number ? `p.${src.page_number}` : '')}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const Section: React.FC<{ icon: React.ReactNode; title: string; children: React.ReactNode }> = ({
  icon,
  title,
  children,
}) => (
  <div>
    <h4 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400 mb-2.5">
      {icon}
      {title}
    </h4>
    {children}
  </div>
);
