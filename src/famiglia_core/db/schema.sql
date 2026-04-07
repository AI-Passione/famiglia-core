-- Consolidated Database Schema for La Passione Inc
-- Cleaned of legacy migration boilerplate

-- 1. Core Agent Actions and Auditing
CREATE TABLE IF NOT EXISTS agent_actions (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  agent_name VARCHAR(50) NOT NULL,
  action_type VARCHAR(100) NOT NULL,
  action_details JSONB,
  is_approval_required BOOLEAN DEFAULT TRUE,
  approval_status VARCHAR(20) DEFAULT 'PENDING',
  don_jimmy_rating INT,
  cost_usd DECIMAL(10,4) DEFAULT 0.0,
  duration_seconds INT,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Content and Newsletters
CREATE TABLE IF NOT EXISTS newsletters (
  id SERIAL PRIMARY KEY,
  source VARCHAR(100),
  title TEXT,
  author VARCHAR(200),
  published_date DATE,
  content_url TEXT,
  full_content TEXT,
  rossini_tldr TEXT,
  key_insights JSONB,
  relevance VARCHAR(10),
  tags TEXT[],
  don_jimmy_rating INT,
  processed_at TIMESTAMPTZ,
  is_posted_to_slack BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Agent Conversations and Messaging
CREATE TABLE IF NOT EXISTS agent_conversations (
  id SERIAL PRIMARY KEY,
  conversation_key VARCHAR(255) NOT NULL UNIQUE,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_messages (
  id SERIAL PRIMARY KEY,
  conversation_id INT NOT NULL REFERENCES agent_conversations(id) ON DELETE CASCADE,
  agent_name VARCHAR(50) NOT NULL,
  sender VARCHAR(120),
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_lookup
  ON agent_messages(conversation_id, created_at DESC);

-- 4. Agent Memories
CREATE TABLE IF NOT EXISTS agent_memories (
  id SERIAL PRIMARY KEY,
  agent_name VARCHAR(50) NOT NULL,
  memory_key VARCHAR(120) NOT NULL,
  memory_value TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (agent_name, memory_key)
);

CREATE INDEX IF NOT EXISTS idx_agent_memories_lookup
  ON agent_memories(agent_name, updated_at DESC);

-- 5. GitHub and Tool Interactions
CREATE TABLE IF NOT EXISTS github_interactions (
  id SERIAL PRIMARY KEY,
  agent_name VARCHAR(50) NOT NULL,
  action_type VARCHAR(50) NOT NULL,
  repo_name VARCHAR(200) NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_github_interactions_lookup
  ON github_interactions(agent_name, action_type, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_github_repos (
  id SERIAL PRIMARY KEY,
  agent_name VARCHAR(50) NOT NULL,
  repo_name VARCHAR(200) NOT NULL,
  permissions JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (agent_name, repo_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_github_repos_lookup
  ON agent_github_repos(agent_name);

CREATE TABLE IF NOT EXISTS prd_github_mappings (
  id             SERIAL PRIMARY KEY,
  notion_page_id VARCHAR(100) NOT NULL UNIQUE,
  repo_name      VARCHAR(200) NOT NULL,
  github_repo_id BIGINT,
  github_project_id  VARCHAR(100),
  github_project_url TEXT,
  prd_title      TEXT,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prd_github_mappings_lookup
  ON prd_github_mappings(notion_page_id);

-- 6. Search Cache
CREATE TABLE IF NOT EXISTS web_search_cache (
  id SERIAL PRIMARY KEY,
  query_text TEXT NOT NULL UNIQUE,
  results JSONB NOT NULL,
  agent_name VARCHAR(50),
  user_prompt TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_web_search_cache_lookup
  ON web_search_cache(query_text);

-- 7. Task Management
CREATE TABLE IF NOT EXISTS recurring_tasks (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  task_payload TEXT NOT NULL,
  priority VARCHAR(10) NOT NULL DEFAULT 'medium',
  expected_agent VARCHAR(50),
  metadata JSONB,
  schedule_config JSONB NOT NULL,
  last_spawned_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CHECK (priority IN ('critical', 'high', 'medium', 'low'))
);

CREATE TABLE IF NOT EXISTS task_instances (
  id SERIAL PRIMARY KEY,
  recurring_task_id INT REFERENCES recurring_tasks(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  task_payload TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'queued',
  priority VARCHAR(10) NOT NULL DEFAULT 'medium',
  created_by_type VARCHAR(20) NOT NULL,
  created_by_name VARCHAR(120) NOT NULL,
  expected_agent VARCHAR(50),
  assigned_agent VARCHAR(50),
  eta_pickup_at TIMESTAMPTZ,
  eta_completion_at TIMESTAMPTZ,
  picked_up_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  result_summary TEXT,
  error_details TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CHECK (status IN ('queued', 'in_progress', 'drafted', 'completed', 'failed', 'cancelled')),
  CHECK (priority IN ('critical', 'high', 'medium', 'low')),
  CHECK (created_by_type IN ('human_user', 'ai_agent'))
);

CREATE INDEX IF NOT EXISTS idx_task_instances_queue ON task_instances(status, priority, eta_pickup_at);
CREATE INDEX IF NOT EXISTS idx_task_instances_history ON task_instances(completed_at DESC) WHERE status IN ('completed', 'failed', 'cancelled');
CREATE INDEX IF NOT EXISTS idx_recurring_tasks_lookup ON recurring_tasks(updated_at);

-- 8. LangGraph Checkpoints (Observability)
CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
  thread_id VARCHAR(255) NOT NULL,
  checkpoint_id VARCHAR(255) NOT NULL,
  parent_id VARCHAR(255),
  checkpoint JSONB NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS idx_langgraph_checkpoints_lookup
  ON langgraph_checkpoints(thread_id, created_at DESC);

CREATE TABLE IF NOT EXISTS langgraph_writes (
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    idx INTEGER NOT NULL,
    channel VARCHAR(255) NOT NULL,
    value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
);

-- 9. User Central Identity (The Don's Ecosystem)
-- Centralized user profile to sync across Slack, Mattermost, and the Web Dashboard.
CREATE TABLE IF NOT EXISTS users (
  id           SERIAL PRIMARY KEY,
  full_name    VARCHAR(255) NOT NULL,
  username     VARCHAR(100) UNIQUE NOT NULL,
  role         VARCHAR(50)  DEFAULT 'don',   -- 'don', 'consigliere', 'soldato'
  avatar_url   TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Maps platform-specific IDs back to the central user.
CREATE TABLE IF NOT EXISTS user_platform_identities (
  id                SERIAL PRIMARY KEY,
  user_id           INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform          VARCHAR(50) NOT NULL, -- 'slack', 'mattermost', 'github', 'notion'
  platform_user_id  VARCHAR(255) NOT NULL,
  metadata          JSONB,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (platform, platform_user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_platform_lookup
  ON user_platform_identities(platform, platform_user_id);

-- 10. User App Settings (for the Command Center owner)
CREATE TABLE IF NOT EXISTS user_settings (
  id                              SERIAL PRIMARY KEY,
  user_id                         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  honorific                       VARCHAR(64) NOT NULL DEFAULT 'Don',
  notifications_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
  background_animations_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
  personal_directive             TEXT,
  system_prompt                  TEXT,
  created_at                      TIMESTAMPTZ DEFAULT NOW(),
  updated_at                      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_settings_user_id
  ON user_settings(user_id);

-- 11. User OAuth Connections (for the Command Center owner)
-- Aligned with the 'users' table if multi-user is needed later.
CREATE TABLE IF NOT EXISTS user_connections (
  id           SERIAL PRIMARY KEY,
  user_id      INT REFERENCES users(id) ON DELETE CASCADE,
  service      VARCHAR(50)  NOT NULL,   -- e.g. 'github', 'google', 'slack', 'notion'
  username     VARCHAR(255),
  avatar_url   TEXT,
  access_token TEXT         NOT NULL,   -- Fernet-encrypted
  scopes       TEXT,
  connected_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, service)
);

CREATE INDEX IF NOT EXISTS idx_user_connections_lookup
  ON user_connections(user_id, service);

-- 12. Intelligence Items (Source of Truth replacing Notion)
CREATE TABLE IF NOT EXISTS intelligence_items (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  content TEXT,
  summary TEXT,
  status VARCHAR(50), -- e.g., 'active', 'archived', 'approved', 'drafted'
  item_type VARCHAR(50) NOT NULL, -- 'dossier', 'blueprint'
  reference_id VARCHAR(100),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intelligence_items_type_status
  ON intelligence_items(item_type, status);
