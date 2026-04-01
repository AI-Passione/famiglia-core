import { useState, useEffect } from 'react';
import type { FamigliaAgent } from '../types';
import { API_BASE, BACKEND_BASE } from '../config';
import { MultiSelect } from './ui/MultiSelect';

interface AgentEditModalProps {
  agent: FamigliaAgent;
  onClose: () => void;
  onSave: () => void;
}

interface Capabilities {
  tools: { id: number; name: string }[];
  skills: { id: number; name: string }[];
  workflows: { id: number; name: string }[];
}

export function AgentEditModal({ agent, onClose, onSave }: AgentEditModalProps) {
  const [formData, setFormData] = useState({
    name: agent.name,
    persona: agent.personality,
    identity: agent.identity,
    aliases: agent.aliases.join(', '),
  });

  const [selectedTools, setSelectedTools] = useState<number[]>(agent.tool_ids);
  const [selectedSkills, setSelectedSkills] = useState<number[]>(agent.skill_ids);
  const [selectedWorkflows, setSelectedWorkflows] = useState<number[]>(agent.workflow_ids);
  
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(agent.avatar_url ? `${BACKEND_BASE}${agent.avatar_url}` : null);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/famiglia/capabilities`)
      .then((res) => res.json())
      .then(setCapabilities);
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // 1. Basic Info
      await fetch(`${API_BASE}/famiglia/agents/${agent.agent_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          persona: formData.persona,
          identity: formData.identity,
          aliases: formData.aliases.split(',').map((s) => s.trim()).filter(Boolean),
        }),
      });

      // 2. Capabilities
      await fetch(`${API_BASE}/famiglia/agents/${agent.agent_id}/capabilities`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tools: selectedTools,
          skills: selectedSkills,
          workflows: selectedWorkflows,
        }),
      });

      // 3. Avatar (if changed)
      if (avatarFile) {
        const formData = new FormData();
        formData.append('file', avatarFile);
        await fetch(`${API_BASE}/famiglia/agents/${agent.agent_id}/avatar`, {
          method: 'POST',
          body: formData,
        });
      }

      onSave();
      onClose();
    } catch (error) {
      console.error('Failed to save agent:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAvatarFile(file);
      setAvatarPreview(URL.createObjectURL(file));
    }
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-300">
      <div className="bg-[#111] border border-outline-variant/30 w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl relative shadow-tertiary/10">
        
        {/* Header */}
        <div className="sticky top-0 z-10 bg-[#111]/95 backdrop-blur-md border-b border-outline-variant/30 px-8 py-6 flex justify-between items-center">
          <div>
            <h2 className="font-headline text-3xl text-white tracking-tight uppercase">
              Edit <span className="text-tertiary">{agent.name}</span>
            </h2>
            <p className="font-body text-xs text-on-surface-variant uppercase tracking-widest mt-1">
              Agent Dossier Configuration
            </p>
          </div>
          <button onClick={onClose} className="text-on-surface-variant hover:text-white transition-colors">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-8 space-y-10">
          
          {/* Section: Avatar & Identity */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="space-y-4">
              <label className="block text-xs font-headline uppercase tracking-widest text-on-surface-variant/70">Profile Picture</label>
              <div className="w-full aspect-square bg-surface-container-low border border-outline-variant/20 relative group overflow-hidden">
                {avatarPreview ? (
                  <img src={avatarPreview} className="w-full h-full object-cover transition-transform group-hover:scale-110 duration-500" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-on-surface-variant/20 italic text-sm">No Preview</div>
                )}
                <label className="absolute inset-x-0 bottom-0 bg-black/60 backdrop-blur-md py-2 text-center text-[10px] uppercase font-headline tracking-tighter text-white opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                  Upload New
                  <input type="file" className="hidden" onChange={onFileChange} accept="image/*" />
                </label>
              </div>
            </div>
            
            <div className="md:col-span-3 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="block text-xs font-headline uppercase tracking-widest text-on-surface-variant/70">Display Name</label>
                  <input
                    type="text"
                    className="w-full bg-surface-container-lowest border border-outline-variant/30 px-4 py-3 text-white focus:border-tertiary focus:outline-none transition-all placeholder:text-on-surface-variant/20"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <label className="block text-xs font-headline uppercase tracking-widest text-on-surface-variant/70">Aliases (comma separated)</label>
                  <input
                    type="text"
                    className="w-full bg-surface-container-lowest border border-outline-variant/30 px-4 py-3 text-white focus:border-tertiary focus:outline-none transition-all placeholder:text-on-surface-variant/20"
                    value={formData.aliases}
                    onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-headline uppercase tracking-widest text-on-surface-variant/70">Core Identity</label>
                <textarea
                  rows={3}
                  className="w-full bg-surface-container-lowest border border-outline-variant/30 px-4 py-3 text-white focus:border-tertiary focus:outline-none transition-all resize-none placeholder:text-on-surface-variant/20"
                  value={formData.identity}
                  onChange={(e) => setFormData({ ...formData, identity: e.target.value })}
                />
              </div>
            </div>
          </div>

          <hr className="border-outline-variant/10" />

          {/* Section: Persona */}
          <div className="space-y-2">
            <label className="block text-xs font-headline uppercase tracking-widest text-on-surface-variant/70 text-tertiary/70">Agent Persona & Persona Directives</label>
            <textarea
              rows={8}
              className="w-full bg-surface-container-lowest border border-outline-variant/30 px-4 py-3 text-white focus:border-tertiary focus:outline-none transition-all resize-none font-mono text-sm leading-relaxed placeholder:text-on-surface-variant/20"
              value={formData.persona}
              onChange={(e) => setFormData({ ...formData, persona: e.target.value })}
            />
          </div>

          <hr className="border-outline-variant/10" />

          {/* Section: Capabilities */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <MultiSelect
              label="Functional Tools"
              options={capabilities?.tools || []}
              selectedIds={selectedTools}
              onChange={setSelectedTools}
            />
            <MultiSelect
              label="Specialized Skills"
              options={capabilities?.skills || []}
              selectedIds={selectedSkills}
              onChange={setSelectedSkills}
            />
            <MultiSelect
              label="Assigned Workflows"
              options={capabilities?.workflows || []}
              selectedIds={selectedWorkflows}
              onChange={setSelectedWorkflows}
            />
          </div>

        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-[#111]/95 backdrop-blur-md border-t border-outline-variant/30 px-8 py-6 flex justify-end gap-4">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-xs font-headline uppercase tracking-widest text-on-surface-variant hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-8 py-2.5 bg-tertiary text-on-tertiary text-xs font-headline uppercase tracking-widest shadow-xl shadow-tertiary/20 hover:brightness-110 active:scale-95 transition-all disabled:opacity-50 disabled:pointer-events-none"
          >
            {isSaving ? 'Synchronizing Soul...' : 'Finalize Edits'}
          </button>
        </div>
      </div>
    </div>
  );
}
