DROP TABLE IF EXISTS agent_skills;
DROP TABLE IF EXISTS skills;

-- Table of specialized agent skills
CREATE TABLE IF NOT EXISTS skills (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  category VARCHAR(50), -- e.g., 'technical', 'strategic', 'analytical'
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Junction table for many-to-many relationship between agents and skills
CREATE TABLE IF NOT EXISTS agent_skills (
  agent_id VARCHAR(50) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
  skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  PRIMARY KEY (agent_id, skill_id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices for faster lookups
CREATE INDEX IF NOT EXISTS idx_agent_skills_agent_id ON agent_skills(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_skills_skill_id ON agent_skills(skill_id);
