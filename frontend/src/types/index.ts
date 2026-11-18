export interface Citation {
  source_id: string;
  filename: string;
  page_number?: number;
  timestamp?: string;
  row_or_item?: string;
  snippet: string;
  relevance_score?: number;
}

export interface ChartSpec {
  chart_type: 'bar' | 'line' | 'scatter' | 'pie' | 'histogram';
  title: string;
  x_axis: string;
  y_axis: string;
  data: Array<Record<string, any>>;
  description: string;
}

export interface AlternativeOption {
  name: string;
  description: string;
  pros: string[];
  cons: string[];
  feasibility_score: number;
  risk_level: 'Low' | 'Medium' | 'High';
  estimated_impact: string;
}

export interface RiskFactor {
  risk: string;
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  mitigation_strategy: string;
}

export interface DecisionReport {
  title: string;
  objective: string;
  executive_summary: string;
  key_findings: string[];
  quantitative_metrics?: Record<string, any>;
  evidence_sources: Citation[];
  alternatives: AlternativeOption[];
  risks_and_limitations: RiskFactor[];
  assumptions: string[];
  final_recommendation: string;
  actionable_next_steps: string[];
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  modality: 'text' | 'document' | 'image' | 'audio' | 'video' | 'dataset' | 'decision';
  file_ids?: string[];
  sources?: Citation[];
  metadata?: {
    chart?: ChartSpec;
    data_table?: Array<Record<string, any>>;
    report?: DecisionReport;
    grounded?: boolean;
    duration_seconds?: number;
    width?: number;
    height?: number;
    [key: string]: any;
  };
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface UploadedFile {
  id: string;
  filename: string;
  file_type: 'document' | 'image' | 'audio' | 'video' | 'dataset';
  file_size: number;
  summary?: string;
  metadata?: Record<string, any>;
  created_at: string;
}
