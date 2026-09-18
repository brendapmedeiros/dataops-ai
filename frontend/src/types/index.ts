export interface SystemStatus {
  banco: {
    conectado: boolean;
    tipo?: string;
    erro?: string;
  };
  api_banco_central: {
    available: boolean;
    status_code?: number;
    source?: string;
    error?: string;
  };
  gemini: {
    configurado: boolean;
    modelo?: string;
    interactions_ativas?: boolean;
  };
}

export interface Scenario {
  nome: string;
  descricao: string;
}

export interface AgentStep {
  speaker: string;
  role: string;
  action: string;
  content: string;
  timestamp?: string;
}

export interface CollaborationInfo {
  status: string;
  rounds: number;
  supervisor_decision: string;
  dialogue?: AgentStep[];
}

export interface HistoryRecord {
  run_id: string;
  recorded_at?: string;
  scenario: string;
  dataset?: string;
  rows_checked?: number;
  failed_checks: number;
  severity: string;
  diagnosis_engine: string;
  quarantined: boolean;
  audit_hash?: string;
  collaboration_status?: string;
  collaboration_summary?: string;
  collaboration?: CollaborationInfo;
  requires_manual_review?: boolean;
  summary: string;
  diagnosis_report_path?: string;
  incident_report_path?: string;
}

export interface GoldRecord {
  date: string;
  value: number;
  series_code: number;
  source: string;
}

export interface QuarantineBatch {
  arquivo: string;
  isolado_em: string;
  tamanho_bytes: number;
  linhas_rejeitadas: number;
}

export interface RunResult {
  run_id: string;
  cenario: string;
  linhas_carregadas: number;
  validacoes_com_falha: number;
  gravidade: string;
  motor_do_diagnostico: string;
  quarentenado: boolean;
  caminho_quarentena?: string;
  audit_hash: string;
  collaboration_status?: string;
  collaboration_summary?: string;
  collaboration?: CollaborationInfo;
  provedor_llm?: string;
  modelo_llm?: string;
  resumo: string;
  precisa_revisao_manual?: boolean;
}
