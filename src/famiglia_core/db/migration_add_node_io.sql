-- Migration to add inputs and outputs to workflow_nodes
ALTER TABLE workflow_nodes ADD COLUMN IF NOT EXISTS inputs TEXT;
ALTER TABLE workflow_nodes ADD COLUMN IF NOT EXISTS outputs TEXT;
