import React, { useState } from 'react';
import {
  Activity,
  Plus,
  MessageSquare,
  Database,
  BarChart3,
  Settings,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { Conversation } from '../../types';

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId?: string;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onOpenKnowledge: () => void;
  onOpenAnalytics: () => void;
  onOpenSettings: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onOpenKnowledge,
  onOpenAnalytics,
  onOpenSettings,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside
      className={`h-screen flex flex-col border-r border-white/[0.06] bg-slate-950/80 backdrop-blur-xl transition-all duration-300 relative z-30 select-none ${
        collapsed ? 'w-[76px]' : 'w-[272px]'
      }`}
    >
      {/* Brand */}
      <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
        {!collapsed ? (
          <div className="flex items-center gap-3">
            <div className="relative w-10 h-10 rounded-2xl bg-gradient-to-br from-brand-500 via-brand-600 to-clinical-500 flex items-center justify-center shadow-lg shadow-brand-600/25">
              <Activity className="w-5 h-5 text-white" strokeWidth={2.4} />
              <span className="absolute -right-0.5 -top-0.5 w-2.5 h-2.5 rounded-full bg-clinical-400 border-2 border-slate-950" />
            </div>
            <div className="min-w-0">
              <h1 className="font-semibold text-[15px] tracking-tight text-white">MedReason</h1>
              <p className="text-[10px] uppercase tracking-[0.16em] text-clinical-400">Clinical RAG</p>
            </div>
          </div>
        ) : (
          <div className="w-10 h-10 mx-auto rounded-2xl bg-gradient-to-br from-brand-500 to-clinical-500 flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" strokeWidth={2.4} />
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 text-slate-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* New case */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full group flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-gradient-to-r from-brand-600 to-clinical-600 hover:from-brand-500 hover:to-clinical-500 text-white text-xs font-medium shadow-lg shadow-brand-600/20 transition-all active:scale-[0.98]"
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          {!collapsed && <span>New clinical case</span>}
        </button>
      </div>

      {/* Search */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search cases..."
              className="w-full bg-white/[0.03] border border-white/[0.07] text-slate-200 text-xs rounded-xl pl-9 pr-3 py-2 placeholder-slate-600 focus:outline-none focus:border-clinical-500/50"
            />
          </div>
        </div>
      )}

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {!collapsed && (
          <p className="px-2 pt-3 pb-1 text-[10px] font-semibold tracking-[0.16em] text-slate-500 uppercase">
            Case history
          </p>
        )}
        {filtered.length === 0 ? (
          !collapsed && (
            <div className="px-3 py-8 text-center">
              <div className="w-9 h-9 mx-auto mb-2 rounded-xl bg-white/[0.04] flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-slate-600" />
              </div>
              <p className="text-[11px] text-slate-600">No cases yet</p>
            </div>
          )
        ) : (
          filtered.map((c) => {
            const active = c.id === activeConversationId;
            return (
              <div
                key={c.id}
                onClick={() => onSelectConversation(c.id)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                  active
                    ? 'bg-brand-500/10 text-brand-200 border border-brand-500/25'
                    : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200 border border-transparent'
                }`}
                title={c.title}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <MessageSquare
                    className={`w-3.5 h-3.5 flex-shrink-0 ${active ? 'text-brand-400' : 'text-slate-600'}`}
                  />
                  {!collapsed && <span className="truncate">{c.title}</span>}
                </div>
                {!collapsed && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(c.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-slate-600 rounded transition-opacity"
                    title="Delete case"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-white/[0.06] space-y-0.5">
        <SidebarItem icon={<Database className="w-4 h-4 text-clinical-400" />} label="Evidence Hub" collapsed={collapsed} onClick={onOpenKnowledge} />
        <SidebarItem icon={<BarChart3 className="w-4 h-4 text-brand-400" />} label="Analytics" collapsed={collapsed} onClick={onOpenAnalytics} />
        <SidebarItem icon={<Settings className="w-4 h-4 text-slate-400" />} label="Settings" collapsed={collapsed} onClick={onOpenSettings} />
        {!collapsed && (
          <div className="mt-2 px-3 py-2 rounded-xl bg-clinical-500/[0.07] border border-clinical-500/15 flex items-start gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-clinical-400 mt-0.5 flex-shrink-0" />
            <p className="text-[10px] leading-relaxed text-slate-500">
              Academic demo only. Use synthetic or de-identified records.
            </p>
          </div>
        )}
      </div>
    </aside>
  );
};

const SidebarItem: React.FC<{
  icon: React.ReactNode;
  label: string;
  collapsed: boolean;
  onClick: () => void;
}> = ({ icon, label, collapsed, onClick }) => (
  <button
    onClick={onClick}
    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-slate-100 hover:bg-white/[0.04] transition-colors"
    title={label}
  >
    <span className="flex-shrink-0">{icon}</span>
    {!collapsed && <span>{label}</span>}
  </button>
);
