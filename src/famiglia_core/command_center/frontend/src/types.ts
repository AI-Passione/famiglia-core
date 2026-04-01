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
  action_details: any;
  approval_status: string;
}

export interface Task {
  id: number;
  title: string;
  task_payload: string;
  status: string;
  priority: string;
  created_at: string;
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
