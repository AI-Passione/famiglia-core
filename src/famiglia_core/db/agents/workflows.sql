DROP TABLE IF EXISTS agent_workflows;
DROP TABLE IF EXISTS workflow_nodes;
DROP TABLE IF EXISTS workflows;

-- Table for orchestration workflows (Graphs)
CREATE TABLE IF NOT EXISTS workflows (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  display_name TEXT,
  description TEXT,
  category VARCHAR(50), -- e.g., 'market_research', 'product_development', 'analytics'
  node_order TEXT[] DEFAULT '{}', -- Array of node names in execution order
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for individual nodes within a workflow
CREATE TABLE IF NOT EXISTS workflow_nodes (
  id SERIAL PRIMARY KEY,
  workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  node_name TEXT NOT NULL,
  description TEXT,
  node_type VARCHAR(50), -- e.g., 'task', 'condition'
  inputs TEXT, -- Extracted function parameters
  outputs TEXT, -- Extracted function return details
  UNIQUE (workflow_id, node_name),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction table for many-to-many relationship between agents and workflows
CREATE TABLE IF NOT EXISTS agent_workflows (
  agent_id VARCHAR(50) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  PRIMARY KEY (agent_id, workflow_id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for faster lookups
CREATE INDEX IF NOT EXISTS idx_agent_workflows_agent_id ON agent_workflows(agent_id);
CREATE INDEX IF NOT EXISTS idx_workflow_nodes_workflow_id ON workflow_nodes(workflow_id);
