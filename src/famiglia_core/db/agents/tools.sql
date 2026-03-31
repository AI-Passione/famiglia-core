DROP TABLE IF EXISTS agent_tools;
DROP TABLE IF EXISTS tools;

-- Table for all available tools in the system
CREATE TABLE IF NOT EXISTS tools (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  plugin VARCHAR(50), -- e.g., 'github', 'notion', 'web_search'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction table for many-to-many relationship between agents and tools
CREATE TABLE IF NOT EXISTS agent_tools (
  agent_id VARCHAR(50) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  tool_id INTEGER NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
  PRIMARY KEY (agent_id, tool_id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for faster lookups
CREATE INDEX IF NOT EXISTS idx_agent_tools_agent_id ON agent_tools(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_tools_tool_id ON agent_tools(tool_id);
