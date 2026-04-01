-- Schema for AI Agents and their Archetypes
-- This is the source of truth for all agents (active & inactive)

DROP TABLE IF EXISTS shared_soul_baseline CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS archetypes CASCADE;

-- Table for Agent Templates/Archetypes
CREATE TABLE IF NOT EXISTS archetypes (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  persona_template TEXT,
  reply_constraints_template TEXT,
  identity_template TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for individual Agents
CREATE TABLE IF NOT EXISTS agents (
  id SERIAL PRIMARY KEY,
  agent_id VARCHAR(50) UNIQUE NOT NULL, -- Logical ID used in code (e.g., 'rossini')
  agent_name TEXT NOT NULL,             -- Display Name
  archetype_id INTEGER REFERENCES archetypes(id) ON DELETE SET NULL,
  aliases TEXT[] NOT NULL DEFAULT '{}',
  persona TEXT,
  reply_constraints TEXT,
  identity TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for common baseline instructions shared by all agents
CREATE TABLE IF NOT EXISTS shared_soul_baseline (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_agents_is_active ON agents(is_active);
CREATE INDEX IF NOT EXISTS idx_agents_archetype_id ON agents(archetype_id);
