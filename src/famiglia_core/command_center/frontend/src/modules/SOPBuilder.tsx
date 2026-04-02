import { useState } from 'react';
import { motion } from 'framer-motion';
import type { SOPWorkflow, SOPNode } from '../types';
import { API_BASE } from '../config';

interface SOPBuilderProps {
  workflow?: SOPWorkflow | null;
  onClose: () => void;
  onSave: () => void;
}

export function SOPBuilder({ workflow, onClose, onSave }: SOPBuilderProps) {
  const [name, setName] = useState(workflow?.name || '');
  const [description, setDescription] = useState(workflow?.description || '');
  const [category, setCategory] = useState(workflow?.category || 'General');
  const [nodes, setNodes] = useState<Partial<SOPNode>[]>(workflow?.nodes || []);
  const [isSaving, setIsSaving] = useState(false);

  const categories = ["General", "Market Research", "Product Development", "Analytics", "Executive"];

  const handleAddNode = () => {
    setNodes(prev => [...prev, { node_name: '', description: '', node_type: 'task' }]);
  };

  const handleRemoveNode = (idx: number) => {
    setNodes(prev => prev.filter((_, i) => i !== idx));
  };

  const handleNodeChange = (idx: number, field: keyof SOPNode, value: string) => {
    setNodes(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: value };
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || nodes.length === 0) return;

    setIsSaving(true);
    try {
      const payload = {
        name,
        description,
        category,
        nodes: nodes.map(n => ({
          node_name: n.node_name || 'Unnamed Node',
          description: n.description || '',
          node_type: n.node_type || 'task'
        }))
      };

      const url = workflow 
        ? `${API_BASE}/sop/workflows/${workflow.id}`
        : `${API_BASE}/sop/workflows`;
      
      const res = await fetch(url, {
        method: workflow ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        onSave();
        onClose();
      }
    } catch (err) {
      console.error("Error saving SOP:", err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-background/80 backdrop-blur-md"
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
        className="w-full max-w-4xl max-h-[90vh] glass-module border border-outline-variant/20 overflow-hidden flex flex-col shadow-2xl"
      >
        <div className="p-8 border-b border-outline-variant/10 flex justify-between items-start bg-surface-container-high/30">
          <div>
            <h3 className="font-headline text-3xl text-primary">
              {workflow ? 'Modify SOP Architecture' : 'Initialize SOP Architecture'}
            </h3>
            <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-2 opacity-70">
              Defining New Structural Logic // {workflow ? `0xUPDATE-${workflow.id}` : '0xNEW_PROTOCOL'}
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-outline hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto custom-scrollbar p-8 space-y-10">
          {/* Metadata Section */}
          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-8 space-y-6">
              <div className="space-y-2">
                <label className="font-label text-[10px] text-outline uppercase tracking-widest pl-1">Protocol Identification</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="E.g. Daily Market Summary Alpha"
                  className="w-full bg-surface-container-highest/30 border border-outline-variant/10 px-4 py-3 font-body text-sm text-on-surface focus:outline-none focus:border-primary/40 focus:bg-surface-container-highest/50 transition-all"
                />
              </div>
              <div className="space-y-2">
                <label className="font-label text-[10px] text-outline uppercase tracking-widest pl-1">Functional Narrative</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="Describe the autonomous intent of this protocol..."
                  rows={2}
                  className="w-full bg-surface-container-highest/30 border border-outline-variant/10 px-4 py-3 font-body text-sm text-[#a38b88] focus:outline-none focus:border-primary/40 focus:bg-surface-container-highest/50 transition-all resize-none"
                />
              </div>
            </div>
            <div className="col-span-4 space-y-6">
              <div className="space-y-2">
                <label className="font-label text-[10px] text-outline uppercase tracking-widest pl-1">SOP Classification</label>
                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  className="w-full bg-surface-container-highest border border-outline-variant/10 px-4 py-[13px] font-label text-[10px] uppercase tracking-widest text-on-surface focus:outline-none focus:border-primary/40"
                >
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Node Builder Section */}
          <div className="space-y-6">
            <div className="flex justify-between items-center border-b border-outline-variant/10 pb-4">
              <h4 className="font-headline text-xl text-[#ffb3b5]">Logic Sequence Builder</h4>
              <button
                type="button"
                onClick={handleAddNode}
                className="bg-tertiary/10 text-tertiary border border-tertiary/20 px-4 py-1.5 font-label text-[9px] uppercase tracking-widest hover:bg-tertiary/20 transition-all flex items-center space-x-2"
              >
                <span className="material-symbols-outlined text-xs">add_circle</span>
                <span>Inject Node</span>
              </button>
            </div>

            <div className="space-y-4">
              {nodes.map((node, idx) => (
                <motion.div
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  key={idx}
                  className="bg-surface-container-high/30 border border-outline-variant/10 p-5 flex items-start space-x-6 group relative"
                >
                  <div className="w-8 h-8 rounded-full bg-surface-container-highest border border-outline-variant/20 flex items-center justify-center font-mono text-[10px] text-tertiary mt-2">
                    {idx + 1}
                  </div>
                  <div className="flex-1 grid grid-cols-12 gap-4">
                    <div className="col-span-4 space-y-1">
                      <label className="font-label text-[8px] text-outline uppercase tracking-tighter">Node ID</label>
                      <input
                        type="text"
                        value={node.node_name}
                        onChange={e => handleNodeChange(idx, 'node_name', e.target.value)}
                        placeholder="FETCH_ASSETS"
                        className="w-full bg-surface-container-highest/50 border border-outline-variant/10 px-3 py-2 font-mono text-[10px] text-on-surface focus:outline-none focus:border-primary/30"
                      />
                    </div>
                    <div className="col-span-6 space-y-1">
                      <label className="font-label text-[8px] text-outline uppercase tracking-tighter">Instruction Detail</label>
                      <input
                        type="text"
                        value={node.description || ''}
                        onChange={e => handleNodeChange(idx, 'description', e.target.value)}
                        placeholder="Retrieve latest market data from..."
                        className="w-full bg-surface-container-highest/50 border border-outline-variant/10 px-3 py-2 font-body text-[10px] text-[#a38b88] focus:outline-none focus:border-primary/30"
                      />
                    </div>
                    <div className="col-span-2 space-y-1">
                      <label className="font-label text-[8px] text-outline uppercase tracking-tighter">Type</label>
                      <select
                        value={node.node_type}
                        onChange={e => handleNodeChange(idx, 'node_type', e.target.value)}
                        className="w-full bg-surface-container-highest/50 border border-outline-variant/10 px-2 py-2 font-label text-[9px] uppercase tracking-tighter text-on-surface focus:outline-none focus:border-primary/30"
                      >
                        <option value="task">TASK</option>
                        <option value="conditional">FORK</option>
                        <option value="entry">START</option>
                        <option value="end">END</option>
                      </select>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveNode(idx)}
                    className="p-1.5 text-outline hover:text-error transition-colors mt-6 opacity-0 group-hover:opacity-100"
                  >
                    <span className="material-symbols-outlined text-[18px]">delete_sweep</span>
                  </button>
                </motion.div>
              ))}

              {nodes.length === 0 && (
                <div className="text-center py-12 bg-surface-container-highest/10 border border-dashed border-outline-variant/10">
                  <p className="font-label text-[10px] text-outline uppercase tracking-widest italic">Sequence Empty. Waiting for logic injection.</p>
                </div>
              )}
            </div>
          </div>
        </form>

        <div className="p-8 border-t border-outline-variant/10 bg-surface-container-high/30 flex justify-end space-x-4">
          <button
            type="button"
            onClick={onClose}
            className="px-8 py-2.5 font-label text-[10px] uppercase tracking-widest text-outline hover:text-on-surface transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={isSaving || !name || nodes.length === 0}
            className="bg-primary text-black px-12 py-2.5 font-bold text-[11px] uppercase tracking-[0.3em] disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-110 active:scale-95 transition-all shadow-xl"
          >
            {isSaving ? 'ARCHIVING...' : 'COMMIT ARCHITECTURE'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
