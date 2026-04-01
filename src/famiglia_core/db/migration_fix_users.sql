-- Manual Migration for La Passione Inc - Fix Missing Tables and Out-of-Sync Schema

-- 1. Create Users Table
CREATE TABLE IF NOT EXISTS users (
  id           SERIAL PRIMARY KEY,
  full_name    VARCHAR(255) NOT NULL,
  username     VARCHAR(100) UNIQUE NOT NULL,
  role         VARCHAR(50)  DEFAULT 'don',
  avatar_url   TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create User Platform Identities Table
CREATE TABLE IF NOT EXISTS user_platform_identities (
  id                SERIAL PRIMARY KEY,
  user_id           INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform          VARCHAR(50) NOT NULL,
  platform_user_id  VARCHAR(255) NOT NULL,
  metadata          JSONB,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (platform, platform_user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_platform_lookup
  ON user_platform_identities(platform, platform_user_id);

-- 3. Create User Settings Table
CREATE TABLE IF NOT EXISTS user_settings (
  id                              SERIAL PRIMARY KEY,
  user_id                         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  honorific                       VARCHAR(64) NOT NULL DEFAULT 'Don',
  notifications_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
  background_animations_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at                      TIMESTAMPTZ DEFAULT NOW(),
  updated_at                      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_settings_user_id
  ON user_settings(user_id);

-- 4. Update User Connections to add user_id
-- We add it as nullable first to avoid issues with existing rows
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_connections' AND column_name='user_id') THEN
        ALTER TABLE user_connections ADD COLUMN user_id INT REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END$$;

-- 5. Create other missing core tables
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

CREATE TABLE IF NOT EXISTS agent_github_repos (
  id SERIAL PRIMARY KEY,
  agent_name VARCHAR(50) NOT NULL,
  repo_name VARCHAR(200) NOT NULL,
  permissions JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (agent_name, repo_name)
);
