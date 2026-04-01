export interface Agent {
  name: string;
  last_active: string | null;
  msg_count: number;
  status: 'idle' | 'thinking' | 'error';
}

export interface Action {
  id: number;
  timestamp: string;
  agent_name: string;
  action_type: string;
  action_details: Record<string, unknown> | null;
  approval_status: string | null;
  cost_usd?: number;
  duration_seconds?: number | null;
  completed_at?: string | null;
}

export interface ScheduleConfig {
  interval_minutes?: number;
  days?: number[];
  hour?: number;
  minute?: number;
}

export interface Task {
  id: number;
  title: string;
  task_payload: string;
  status: string;
  priority: string;
  created_at: string;
  expected_agent?: string | null;
  assigned_agent?: string | null;
  created_by_name?: string;
  eta_pickup_at?: string | null;
  eta_completion_at?: string | null;
  picked_up_at?: string | null;
  completed_at?: string | null;
  result_summary?: string | null;
  recurring_task_id?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface RecurringTask {
  id: number;
  title: string;
  task_payload: string;
  priority: string;
  expected_agent?: string | null;
  metadata?: Record<string, unknown> | null;
  schedule_config: ScheduleConfig;
  last_spawned_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'node' | 'conditional' | 'entry' | 'end';
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string;
}

export interface GraphDefinition {
  id: string;
  name: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface MissionLogEntry {
  id: string;
  graph_id: string;
  timestamp: string;
  status: 'success' | 'failure' | 'running';
  duration: string;
  initiator: string;
}

export interface AppSettings {
  honorific: string;
  notificationsEnabled: boolean;
  backgroundAnimationsEnabled: boolean;
}

export interface FamigliaAgent {
  id: string;
  agent_id: string;
  name: string;
  role: string;
  status: string;
  aliases: string[];
  personality: string;
  identity: string;
  skills: string[];
  tools: string[];
  workflows: string[];
  latest_conversation_snippet: string;
  last_active: string | null;
}
