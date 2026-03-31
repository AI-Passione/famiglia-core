DROP TABLE IF EXISTS agent_resources;
DROP TABLE IF EXISTS resources;

-- Table for external resources, documentation, and channels
CREATE TABLE IF NOT EXISTS resources (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  url TEXT,
  type VARCHAR(50), -- e.g., 'documentation', 'database', 'channel'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_resources (
  agent_id VARCHAR(50) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
  PRIMARY KEY (agent_id, resource_id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for faster lookups
CREATE INDEX IF NOT EXISTS idx_agent_resources_agent_id ON agent_resources(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_resources_resource_id ON agent_resources(resource_id);
