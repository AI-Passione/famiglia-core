import { useState } from 'react';
import { motion } from 'framer-motion';
import { API_BASE } from '../config';

interface CategoryCreatorProps {
  onClose: () => void;
  onSave: () => void;
}

export function CategoryCreator({ onClose, onSave }: CategoryCreatorProps) {
  const [displayName, setDisplayName] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayName.trim()) return;

    setIsSaving(true);
    try {
      const name = displayName.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
      const res = await fetch(`${API_BASE}/sop/categories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          display_name: displayName.trim()
        }),
      });

      if (res.ok) {
        onSave();
        onClose();
      }
    } catch (err) {
      console.error("Error creating category:", err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[110] flex items-center justify-center p-6 bg-background/90 backdrop-blur-xl"
    >
      <motion.div
        initial={{ scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.9, y: 20 }}
        className="w-full max-w-lg glass-module border border-primary/20 p-10 relative overflow-hidden shadow-[0_0_50px_rgba(var(--primary-rgb),0.1)]"
      >
        {/* Decorative Corner */}
        <div className="absolute top-0 right-0 w-20 h-20 bg-primary/5 blur-3xl rounded-full -mr-10 -mt-10"></div>
        
        <div className="space-y-8 relative z-10">
          <div>
            <h3 className="font-headline text-2xl text-primary">Initialize Structural Tier</h3>
            <p className="font-label text-[9px] text-tertiary uppercase tracking-[0.3em] mt-2 opacity-70">
              Defining New Operational Branch // 0xCAT
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-3">
              <label className="font-label text-[10px] text-outline uppercase tracking-widest pl-1">
                Category Designation
              </label>
              <input
                type="text"
                autoFocus
                required
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="E.g. Special Operations"
                className="w-full bg-surface-container-highest/50 border border-outline-variant/20 px-5 py-4 font-headline text-xl text-on-surface focus:outline-none focus:border-primary/50 focus:bg-surface-container-highest transition-all shadow-inner"
              />
              <p className="font-mono text-[8px] text-outline opacity-40 uppercase tracking-tighter pl-1">
                Internal Slug: {displayName.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '') || '...'}
              </p>
            </div>

            <div className="flex justify-end space-x-6 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="font-label text-[10px] uppercase tracking-widest text-outline hover:text-on-surface transition-colors"
              >
                Abort
              </button>
              <button
                type="submit"
                disabled={isSaving || !displayName.trim()}
                className="bg-primary text-black px-10 py-3 font-bold text-[11px] uppercase tracking-[0.3em] disabled:opacity-30 disabled:cursor-not-allowed hover:brightness-110 active:scale-95 transition-all shadow-lg"
              >
                {isSaving ? 'Establishing...' : 'Initialize Tier'}
              </button>
            </div>
          </form>
        </div>

        {/* Bottom Accent */}
        <div className="absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
      </motion.div>
    </motion.div>
  );
}
