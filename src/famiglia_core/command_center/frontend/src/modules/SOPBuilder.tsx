import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { SOPWorkflow, SOPNode, Category } from '../types';
import { API_BASE } from '../config';

interface SOPBuilderProps {
  workflow?: SOPWorkflow | null;
  onClose: () => void;
  onSave: () => void;
  initialAddCategory?: boolean;
}

export function SOPBuilder({ workflow, onClose, onSave }: SOPBuilderProps) {
  const [displayName, setDisplayName] = useState(workflow?.display_name || '');
  const [name, setName] = useState(workflow?.name || '');
  const [description, setDescription] = useState(workflow?.description || '');
  const [categoryId, setCategoryId] = useState<number | undefined>(workflow?.category_id);
  const [nodes, setNodes] = useState<Partial<SOPNode>[]>(workflow?.nodes || []);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isManualId, setIsManualId] = useState(!!workflow?.name);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/sop/categories`);
      if (res.ok) {
        const data = await res.json();
        setCategories(data);
        if (!categoryId && data.length > 0) {
          setCategoryId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  }, [categoryId]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const handleDisplayNameChange = (val: string) => {
    setDisplayName(val);
    if (!isManualId) {
      setName(val.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''));
    }
  };

  const handleAddNode = () => {
    setNodes([...nodes, { node_name: '', description: '', node_type: 'task' }]);
  };

  const handleRemoveNode = (idx: number) => {
    setNodes(nodes.filter((_, i) => i !== idx));
  };

  const handleNodeChange = (idx: number, field: keyof SOPNode, value: string) => {
    const newNodes = [...nodes];
    newNodes[idx] = { ...newNodes[idx], [field]: value };
    setNodes(newNodes);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const payload = {
        name,
        display_name: displayName,
        description,
        category_id: categoryId,
        nodes: nodes.map(n => ({
          node_name: n.node_name,
          description: n.description,
          node_type: n.node_type || 'task'
        }))
      };

      const url = workflow 
        ? `${API_BASE}/sop/workflows/${workflow.id}`
        : `${API_BASE}/sop/workflows`;
      
      const method = workflow ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
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
      className="fixed inset-0 z-[100] bg-background/80 backdrop-blur-md p-8 overflow-y-auto custom-scrollbar"
    >
      <div className="max-w-5xl mx-auto space-y-12 pb-24">
        {/* Header */}
        <div className="flex justify-between items-start pt-12">
          <div>
            <h2 className="font-headline text-4xl text-primary">SOP Architect</h2>
            <p className="font-label text-xs text-tertiary uppercase tracking-[0.4em] mt-2 opacity-60">
              Structural Intelligence Protocol Initialization // 0xBUILD
            </p>
          </div>
          <button 
            onClick={onClose}
            className="text-outline hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined text-4xl">close</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-12 gap-12">
          {/* Metadata Sidebar */}
          <div className="col-span-12 lg:col-span-4 space-y-10">
            <section className="glass-module border border-outline-variant/10 p-8 space-y-8">
              <div className="space-y-4">
                <label className="font-label text-[10px] text-outline uppercase tracking-widest block">Protocol Category</label>
                <div className="relative group">
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(Number(e.target.value))}
                    className="w-full bg-surface-container-highest border border-outline-variant/20 px-4 py-3 font-body text-sm text-on-surface focus:outline-none focus:border-primary/50 transition-all appearance-none pr-10"
                  >
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.display_name}</option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-outline text-lg">expand_more</span>
                </div>
              </div>

              <div className="space-y-4">
                <label className="font-label text-[10px] text-outline uppercase tracking-widest block">Display Name</label>
                <input
                  type="text"
                  required
                  placeholder="E.g. PRD Review Strategy"
                  value={displayName}
                  onChange={e => handleDisplayNameChange(e.target.value)}
                  className="w-full bg-surface-container-highest border border-outline-variant/20 px-4 py-3 font-headline text-lg text-on-surface focus:outline-none focus:border-primary/50 transition-all"
                />
              </div>

              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <label className="font-label text-[10px] text-outline uppercase tracking-widest block">Technical Slug</label>
                  <button 
                    type="button" 
                    onClick={() => setIsManualId(!isManualId)}
                    className="font-mono text-[8px] text-primary uppercase tracking-widest hover:underline"
                  >
                    {isManualId ? 'Unlock Auto' : 'Manual Edit'}
                  </button>
                </div>
                <input
                  type="text"
                  required
                  disabled={!isManualId}
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-black/20 border border-outline-variant/10 px-4 py-2 font-mono text-xs text-secondary focus:outline-none focus:border-secondary/50 disabled:opacity-50 transition-all"
                />
              </div>

              <div className="space-y-4">
                <label className="font-label text-[10px] text-outline uppercase tracking-widest block">Description</label>
                <textarea
                  rows={4}
                  placeholder="Define the strategic objective of this SOP..."
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  className="w-full bg-surface-container-highest border border-outline-variant/20 px-4 py-3 font-body text-sm text-on-surface focus:outline-none focus:border-primary/50 transition-all resize-none"
                />
              </div>
            </section>
          </div>

          {/* Logic Node Area */}
          <div className="col-span-12 lg:col-span-8 space-y-10">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <span className="material-symbols-outlined text-primary text-xl">account_tree</span>
                <h4 className="font-label text-sm uppercase tracking-[0.3em] text-on-surface">Execution Sequence</h4>
              </div>
              <button
                type="button"
                onClick={handleAddNode}
                className="bg-primary/10 text-primary border border-primary/20 px-6 py-2 font-label text-[10px] uppercase tracking-widest hover:bg-primary/20 transition-all flex items-center space-x-2"
              >
                <span className="material-symbols-outlined text-sm">add</span>
                <span>Insert Node</span>
              </button>
            </div>

            <div className="space-y-4">
              <AnimatePresence>
                {nodes.map((node, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    className="glass-module border border-outline-variant/10 p-6 space-y-4 relative group"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex items-center space-x-4">
                        <span className="w-6 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center font-mono text-[10px] text-primary">
                          {idx + 1}
                        </span>
                        <input
                          type="text"
                          required
                          placeholder="Node Designation"
                          value={node.node_name}
                          onChange={e => handleNodeChange(idx, 'node_name', e.target.value)}
                          className="bg-transparent border-b border-outline-variant/20 focus:border-primary/50 focus:outline-none font-headline text-lg text-on-surface transition-all w-64"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveNode(idx)}
                        className="text-outline opacity-0 group-hover:opacity-100 hover:text-error transition-all"
                      >
                        <span className="material-symbols-outlined">delete</span>
                      </button>
                    </div>
                    <div className="grid grid-cols-12 gap-6">
                      <div className="col-span-9">
                        <input
                          type="text"
                          placeholder="Instructional metadata..."
                          value={node.description || ''}
                          onChange={e => handleNodeChange(idx, 'description', e.target.value)}
                          className="w-full bg-black/10 border border-outline-variant/10 px-4 py-2 font-body text-xs text-outline focus:outline-none focus:border-primary/30 transition-all"
                        />
                      </div>
                      <div className="col-span-3">
                        <select
                          value={node.node_type}
                          onChange={e => handleNodeChange(idx, 'node_type', e.target.value)}
                          className="w-full bg-black/10 border border-outline-variant/10 px-3 py-2 font-mono text-[10px] uppercase text-tertiary focus:outline-none"
                        >
                          <option value="task">Autonomous Task</option>
                          <option value="condition">Logical Pivot</option>
                          <option value="human">Manual Override</option>
                        </select>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {nodes.length === 0 && (
                <div className="py-20 text-center border border-dashed border-outline-variant/20 opacity-40">
                  <p className="font-label text-[10px] uppercase tracking-widest">No Logic Nodes Defined</p>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-8">
              <button
                type="submit"
                disabled={isSaving || nodes.length === 0}
                className="bg-primary text-black px-12 py-4 font-bold text-xs uppercase tracking-[0.4em] disabled:opacity-30 disabled:cursor-not-allowed hover:brightness-110 active:scale-95 transition-all shadow-glow"
              >
                {isSaving ? 'Establishing Protocol...' : (workflow ? 'Synchronize Protocol' : 'Initialize Protocol')}
              </button>
            </div>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
