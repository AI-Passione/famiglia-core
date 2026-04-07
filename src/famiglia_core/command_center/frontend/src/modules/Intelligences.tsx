import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { IntelligenceItem } from '../types';
import { API_BASE } from '../config';

export function Intelligences() {
  const [items, setItems] = useState<IntelligenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchIntelligence = async () => {
      try {
        const response = await fetch(`${API_BASE}/intelligence/`);
        if (!response.ok) {
          throw new Error('Failed to fetch intelligence data');
        }
        const data = await response.json();
        setItems(data);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchIntelligence();
  }, []);

  const dossiers = items.filter(item => item.item_type === 'dossier');
  const blueprints = items.filter(item => item.item_type === 'blueprint');

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[60vh]">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-primary rounded-full border-t-transparent animate-spin"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] text-error">
        <span className="material-symbols-outlined text-6xl mb-4">error</span>
        <h2 className="text-2xl font-headline uppercase tracking-widest">Access Denied</h2>
        <p className="text-sm mt-2 opacity-60">System failure: {error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="mt-6 px-6 py-2 bg-surface-container-high hover:bg-surface-bright text-white text-xs font-bold font-label transition-all"
        >
          RETRY CONNECTION
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col gap-12">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-4xl md:text-5xl font-black font-headline text-white tracking-tight">Intelligences</h1>
          <p className="text-outline font-body mt-2">Aggregated Market Research & Strategic Blueprints</p>
        </motion.div>
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-surface-container-high hover:bg-surface-bright text-white text-sm font-bold font-label transition-all">
            GENERATE SUMMARY
          </button>
          <button className="px-5 py-2.5 bg-primary-container text-primary hover:bg-primary-container/80 text-sm font-bold font-label transition-all">
            EXPORT RAW
          </button>
        </div>
      </div>

      {/* Executive Dossiers */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold font-headline text-white flex items-center gap-3">
            Executive Dossiers
            <span className="text-[10px] font-label font-medium px-2 py-0.5 border border-outline-variant/30 rounded text-outline uppercase tracking-wider">Rossini Research Dept.</span>
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {dossiers.map((dossier, idx) => (
            <motion.div 
              key={dossier.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ y: -4 }}
              className="bg-surface-container-low p-6 rounded-lg group hover:bg-surface-container transition-all border border-outline-variant/5 hover:border-outline-variant/20"
            >
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-surface-container-lowest rounded shadow-inner">
                  <span className="material-symbols-outlined text-tertiary">folder_managed</span>
                </div>
                <div className="flex items-center gap-2 font-label text-[10px] uppercase font-bold tracking-widest text-tertiary">
                  <span className={`h-1.5 w-1.5 rounded-full ${dossier.status?.toLowerCase() === 'active' ? 'bg-tertiary shadow-[0_0_8px_#eac34a]' : 'bg-outline/40'}`}></span>
                  {dossier.status || 'Active'}
                </div>
              </div>
              <h3 className="text-xl font-headline text-white mb-2">{dossier.title}</h3>
              <p className="text-on-surface-variant text-sm mb-6 leading-relaxed line-clamp-3">
                {dossier.content}
              </p>
              <div className="flex items-center justify-between border-t border-outline-variant/10 pt-4 mt-auto">
                <span className="text-[10px] font-label text-outline uppercase">Ref: {dossier.reference_id}</span>
                <a className="text-xs font-bold font-label text-primary hover:underline uppercase" href="#">View Full Report</a>
              </div>
            </motion.div>
          ))}
          {dossiers.length === 0 && (
            <div className="col-span-full py-20 bg-surface-container-lowest/50 rounded-lg border border-dashed border-outline-variant/20 flex flex-col items-center justify-center opacity-40">
              <span className="material-symbols-outlined text-4xl mb-2">inventory_2</span>
              <p className="font-label text-xs uppercase tracking-widest">No Active Dossiers Found</p>
            </div>
          )}
        </div>
      </section>

      {/* Project Blueprints & PRDs */}
      <section>
        <h2 className="text-2xl font-bold font-headline text-white mb-6">Project Blueprints & PRDs</h2>
        <div className="bg-surface-container-lowest rounded-lg overflow-hidden border border-outline-variant/5 shadow-2xl glass-effect">
          <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-surface-container-low border-b border-outline-variant/10 font-label text-[10px] uppercase font-bold tracking-widest text-outline">
            <div className="col-span-6">Document Name</div>
            <div className="col-span-3">Status</div>
            <div className="col-span-3 text-right">Last Sync</div>
          </div>
          <div className="flex flex-col">
            {blueprints.map((blueprint, idx) => (
              <motion.div 
                key={blueprint.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + (idx * 0.05) }}
                className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-surface-container transition-all group cursor-pointer border-b border-outline-variant/5 last:border-0"
              >
                <div className="col-span-6 flex items-center gap-3">
                  <span className={`material-symbols-outlined text-lg ${blueprint.status?.toLowerCase() === 'approved' ? 'text-primary' : 'text-outline'}`}>
                    {blueprint.metadata.icon || 'description'}
                  </span>
                  <span className="text-white font-medium text-sm group-hover:text-primary transition-colors">{blueprint.title}</span>
                </div>
                <div className="col-span-3">
                  <span className={`px-2 py-0.5 text-[10px] font-label font-bold rounded uppercase ${
                    blueprint.status?.toLowerCase() === 'approved' 
                      ? 'bg-on-tertiary-fixed-variant text-tertiary' 
                      : 'bg-surface-container-high text-outline'
                  }`}>
                    {blueprint.status}
                  </span>
                </div>
                <div className="col-span-3 text-right text-outline text-[10px] font-label">
                  {blueprint.metadata.last_sync || 'N/A'}
                </div>
              </motion.div>
            ))}
            {blueprints.length === 0 && (
              <div className="py-12 flex flex-col items-center justify-center opacity-30">
                <span className="material-symbols-outlined text-4xl mb-2">description</span>
                <p className="font-label text-xs uppercase tracking-widest">No Blueprints Registered</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <style dangerouslySetInnerHTML={{ __html: `
        .glass-effect {
          background: linear-gradient(135deg, rgba(28, 27, 27, 0.4) 0%, rgba(18, 18, 18, 0.6) 100%);
          backdrop-filter: blur(10px);
        }
      `}} />
    </div>
  );
}
