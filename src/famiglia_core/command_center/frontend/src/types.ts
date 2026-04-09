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

export interface ActionLog {
  id: number;
  timestamp: string;
  agent_name: string;
  action_type: string;
  action_details: Record<string, any> | null;
  approval_status: string | null;
  cost_usd: number;
  duration_seconds: number | null;
  completed_at: string | null;
}

export interface PaginatedActions {
  actions: ActionLog[];
  total: number;
}

export interface PaginatedTasks {
  tasks: Task[];
  total: number;
}

export interface ConversationLog {
  id: number;
  conversation_key: string;
  metadata?: Record<string, any> | null;
  updated_at: string;
  latest_message?: string | null;
  latest_agent?: string | null;
}

export interface PaginatedConversations {
  conversations: ConversationLog[];
  total: number;
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
  category?: string;
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
  famigliaName: string;
  notificationsEnabled: boolean;
  backgroundAnimationsEnabled: boolean;
  personalDirective: string;
  systemPrompt: string;
}

export interface FamigliaAgent {
  id: string;
  agent_id: string;
  name: string;
  role: string;
  is_active: boolean;
  status: string;
  aliases: string[];
  personality: string;
  identity: string;
  skills: string[];
  skill_ids: number[];
  tools: string[];
  tool_ids: number[];
  workflows: string[];
  workflow_ids: number[];
  latest_conversation_snippet: string;
  last_active: string | null;
  avatar_url: string | null;
}

export interface EngineRoomPort {
  host_port: number;
  container_port: number;
  raw: string;
}

export interface EngineRoomTool {
  slug: string;
  name: string;
  category: string;
  description: string;
  configured: boolean;
  connected: boolean;
  status: string;
  detail: string;
}

export interface EngineRoomDockerService {
  name: string;
  image?: string | null;
  profiles: string[];
  ports: EngineRoomPort[];
  has_healthcheck: boolean;
  reachable: boolean;
  state: string;
  health: string;
  source: string;
}

export interface EngineRoomObservabilityItem {
  name: string;
  service_name: string;
  description: string;
  url: string;
  configured: boolean;
  reachable: boolean;
  state: string;
  health: string;
}

export interface EngineRoomMetric {
  label: string;
  value: string;
  hint: string;
  tone: 'good' | 'warn' | 'critical' | 'neutral';
}

export interface EngineRoomSnapshot {
  scope: string;
  generated_at: string;
  host: {
    hostname: string;
    platform: {
      system: string;
      release: string;
      machine: string;
      python: string;
    };
    uptime: {
      seconds: number | null;
      display: string;
      source: string;
    };
    cpu: {
      cores: number;
      load_average: number[] | null;
      estimated_load_percent: number | null;
      source: string;
    };
    memory: {
      total_bytes: number | null;
      used_bytes: number | null;
      available_bytes: number | null;
      usage_percent: number | null;
      source: string;
    };
    disk: {
      path: string;
      total_bytes: number;
      used_bytes: number;
      free_bytes: number;
      usage_percent: number | null;
    };
  };
  tools: {
    items: EngineRoomTool[];
    summary: {
      total: number;
      ready: number;
      connected: number;
      configured: number;
    };
  };
  docker: {
    available: boolean;
    compose_file: string;
    diagnostics: string[];
    services: EngineRoomDockerService[];
    summary: {
      declared: number;
      reachable: number;
      live: number;
      healthy: number;
    };
  };
  observability: {
    items: EngineRoomObservabilityItem[];
    metrics: EngineRoomMetric[];
    summary: {
      total: number;
      configured: number;
      reachable: number;
    };
  };
}

export interface Category {
  id: number;
  name: string;
  display_name: string;
  created_at: string;
}

export interface CategoryCreate {
  name: string;
  display_name: string;
}

export interface SOPNode {
  id?: number;
  workflow_id?: number;
  node_name: string;
  description: string | null;
  node_type: string;
}

export interface SOPWorkflow {
  id: number;
  name: string;
  display_name: string | null;
  description: string | null;
  category_id?: number;
  category_name?: string;
  category_display_name?: string;
  node_order: string[];
  nodes: SOPNode[];
  created_at: string;
  updated_at: string;
}

export interface SOPWorkflowCreate {
  name: string;
  display_name: string | null;
  description: string | null;
  category_id?: number;
  nodes: Omit<SOPNode, 'id' | 'workflow_id'>[];
}

export interface IntelligenceItem {
  id: number;
  notion_id: string | null;
  title: string;
  content: string | null;
  summary: string | null;
  status: string | null;
  item_type: 'market_research' | 'prd' | 'project' | 'analysis' | string;
  icon: any | null;
  cover: any | null;
  properties: Record<string, any>;
  parent: any | null;
  url: string | null;
  public_url: string | null;
  in_trash: boolean;
  created_time: string | null;
  last_edited_time: string | null;
  created_at: string;
  updated_at: string;
}
