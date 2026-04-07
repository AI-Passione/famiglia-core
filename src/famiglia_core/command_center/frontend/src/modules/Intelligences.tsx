import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { IntelligenceItem } from '../types';
import { API_BASE } from '../config';

export function Intelligences() {
  const [items, setItems] = useState<IntelligenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [syncing, setSyncing] = useState(false);

  const fetchIntelligence = async () => {
    setLoading(true);
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

  useEffect(() => {
    fetchIntelligence();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await fetch(`${API_BASE}/intelligence/sync`, { method: 'POST' });
      if (!response.ok) throw new Error('Sync failed');
      await fetchIntelligence();
    } catch (err) {
      console.error(err);
      alert('Failed to sync with Notion. Check backend logs.');
    } finally {
      setSyncing(false);
    }
  };

  const selectedItem = useMemo(() => 
    items.find(item => item.id === selectedItemId), 
  [items, selectedItemId]);

  const filteredItems = useMemo(() => {
    return items.filter(item => 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.content || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      Object.entries(item.properties || {}).some(([_, val]) => String(val).toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [items, searchQuery]);

  const dossiers = filteredItems.filter(item => item.item_type === 'dossier');
  const blueprints = filteredItems.filter(item => item.item_type === 'blueprint');

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
    <div className="flex-1 flex h-full overflow-hidden bg-surface-container-lowest/30 backdrop-blur-sm">
      {/* Sidebar Navigation */}
      <div className="w-80 border-r border-outline-variant/10 flex flex-col bg-surface-container-lowest/50 backdrop-blur-md">
        <div className="p-4 border-b border-outline-variant/5">
          <div className="relative group">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm group-focus-within:text-primary transition-colors">search</span>
            <input 
              type="text" 
              placeholder="Search intelligence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface-container-low border border-outline-variant/10 rounded-lg py-2 pl-10 pr-4 text-xs text-white placeholder:text-outline focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all font-body"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-6">
          {/* Executive Dossiers Group */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between">
              <span className="text-[10px] font-black font-label text-outline uppercase tracking-widest">Executive Dossiers</span>
              <span className="text-[10px] font-bold text-tertiary bg-tertiary/10 px-1.5 py-0.5 rounded">{dossiers.length}</span>
            </div>
            <div className="space-y-1">
              {dossiers.map(item => (
                <SidebarItem 
                  key={item.id}
                  item={item}
                  isSelected={selectedItemId === item.id}
                  onClick={() => setSelectedItemId(item.id)}
                />
              ))}
            </div>
          </div>

          {/* Project Blueprints Group */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between">
              <span className="text-[10px] font-black font-label text-outline uppercase tracking-widest">Project Blueprints</span>
              <span className="text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded">{blueprints.length}</span>
            </div>
            <div className="space-y-1">
              {blueprints.map(item => (
                <SidebarItem 
                  key={item.id}
                  item={item}
                  isSelected={selectedItemId === item.id}
                  onClick={() => setSelectedItemId(item.id)}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-outline-variant/5 bg-surface-container-low/30 space-y-2">
          <button 
            onClick={handleSync}
            disabled={syncing}
            className={`w-full py-2 flex items-center justify-center gap-2 text-white text-[10px] font-black font-label tracking-widest uppercase transition-all rounded ${
              syncing ? 'bg-surface-container-high opacity-50 cursor-not-allowed' : 'bg-primary/20 hover:bg-primary/40 border border-primary/30'
            }`}
          >
            <span className={`material-symbols-outlined text-sm ${syncing ? 'animate-spin' : ''}`}>
              {syncing ? 'sync' : 'sync_alt'}
            </span>
            {syncing ? 'SYNCING...' : 'SYNC WITH NOTION'}
          </button>
          <button className="w-full py-2 bg-surface-container-high hover:bg-surface-bright text-white text-[10px] font-black font-label tracking-widest uppercase transition-all rounded">
            GENERATE SUMMARY
          </button>
        </div>
      </div>

      {/* Main Content Viewport */}
      <div className="flex-1 overflow-y-auto custom-scrollbar relative">
        <AnimatePresence mode="wait">
          {selectedItem ? (
            <motion.div 
              key={selectedItem.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="min-h-full flex flex-col"
            >
              {/* Cover Image Area */}
              <div className="relative h-64 w-full bg-surface-container-high overflow-hidden">
                {selectedItem.cover ? (
                  <img 
                    src={selectedItem.cover.external?.url || selectedItem.cover.file?.url} 
                    alt="Cover" 
                    className="w-full h-full object-cover opacity-60 grayscale-[30%] blur-[1px] hover:blur-0 transition-all duration-700"
                  />
                ) : (
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/5 to-transparent anim-pulse-slow" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest via-transparent to-transparent" />
                
                {/* Floating Title & Icon */}
                <div className="absolute bottom-8 left-12 right-12 flex items-end gap-6">
                  <div className="w-24 h-24 rounded-2xl bg-surface-container-highest/80 backdrop-blur-xl border border-white/10 flex items-center justify-center text-4xl shadow-2xl transform hover:scale-110 transition-transform">
                    {renderNotionIcon(selectedItem.icon) || (selectedItem.item_type === 'dossier' ? '📂' : '📑')}
                  </div>
                  <div className="flex-1 pb-2">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-2 py-0.5 rounded bg-primary/20 text-primary text-[10px] font-black uppercase tracking-tighter border border-primary/30">
                        {selectedItem.item_type}
                      </span>
                      <span className="text-white/40 text-[10px] font-mono tracking-tighter">
                        {selectedItem.notion_id?.substring(0, 8)}...
                      </span>
                    </div>
                    <h1 className="text-4xl font-black text-white font-title tracking-tight drop-shadow-lg">
                      {selectedItem.title}
                    </h1>
                  </div>
                </div>
              </div>

              {/* Document Metadata / Properties */}
              <div className="px-12 py-8 grid grid-cols-1 md:grid-cols-4 gap-6 border-b border-outline-variant/10">
                <PropertyItem icon="analytics" label="Status" value={selectedItem.status || 'Active'} isStatus />
                <PropertyItem icon="link" label="Source" value="Notion" href={selectedItem.url || '#'} />
                <PropertyItem icon="schedule" label="Created" value={selectedItem.created_time ? new Date(selectedItem.created_time).toLocaleDateString() : 'N/A'} />
                <PropertyItem icon="history" label="Last Edited" value={selectedItem.last_edited_time ? new Date(selectedItem.last_edited_time).toLocaleDateString() : 'N/A'} />
              </div>

              {/* Content Area */}
              <div className="px-24 py-12 flex-1 max-w-5xl">
                {/* Summary Callout */}
                <div className="mb-12 p-6 bg-tertiary/5 rounded-xl border border-tertiary/20 flex gap-4">
                  <span className="material-symbols-outlined text-tertiary text-2xl">auto_awesome</span>
                  <div>
                    <span className="text-[10px] font-black font-label text-tertiary uppercase tracking-widest mb-1 block">AI-Generated Intelligence Summary</span>
                    <p className="text-sm text-on-surface-variant font-body leading-relaxed italic">
                      This {selectedItem.item_type} focuses on {selectedItem.title.toLowerCase()}. Key patterns indicate significant market movement. Recommended action: Deep-dive into technical layer.
                    </p>
                  </div>
                </div>

                {/* Main Content Rendering */}
                <div className="prose prose-invert prose-sm max-w-none font-body text-white/80 leading-relaxed space-y-6">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {selectedItem.content || ''}
                  </ReactMarkdown>
                </div>
              </div>
            </motion.div>
          ) : (
            <IntelligenceHome items={items} onSelect={setSelectedItemId} />
          )}
        </AnimatePresence>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.1);
        }
        .animate-pulse-slow {
          animation: pulse-slow 8s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes pulse-slow {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.6; }
        }
      `}} />
    </div>
  );
}

function renderNotionIcon(icon: any) {
  if (!icon) return null;
  if (icon.type === 'emoji') return icon.emoji;
  if (icon.type === 'external') return <img src={icon.external.url} className="w-5 h-5 object-contain" alt="Icon" />;
  if (icon.type === 'file') return <img src={icon.file.url} className="w-5 h-5 object-contain" alt="Icon" />;
  return null;
}

function SidebarItem({ item, isSelected, onClick }: { item: IntelligenceItem, isSelected: boolean, onClick: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full text-left p-2.5 rounded-lg flex items-center gap-3 transition-all group ${
        isSelected 
          ? 'bg-primary/10 border border-primary/20 shadow-lg shadow-primary/5' 
          : 'hover:bg-surface-container-high border border-transparent hover:border-outline-variant/10'
      }`}
    >
      <div className={`w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 transition-colors
        ${isSelected ? 'bg-primary/30 text-primary' : 'bg-surface-container-high text-on-surface-variant'}`}>
        {renderNotionIcon(item.icon) || (
          <span className="material-symbols-outlined text-lg">
            {item.item_type === 'dossier' ? 'folder' : 'article'}
          </span>
        )}
      </div>
      <div className="flex-1 truncate">
        <p className={`text-xs font-medium truncate transition-colors ${
          isSelected ? 'text-white font-bold' : 'text-outline group-hover:text-white'
        }`}>{item.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className={`w-1 h-1 rounded-full ${
            item.status?.toLowerCase() === 'approved' || item.status?.toLowerCase() === 'active' 
              ? 'bg-tertiary shadow-[0_0_5px_rgba(234,195,74,0.5)]' 
              : 'bg-outline/40'
          }`}></span>
          <span className="text-[9px] font-label font-bold text-outline uppercase tracking-tighter">{item.status}</span>
        </div>
      </div>
      {isSelected && (
        <motion.div layoutId="active-indicator" className="w-1 h-4 bg-primary rounded-full" />
      )}
    </button>
  );
}

function PropertyItem({ icon, label, value, isStatus, href }: { icon: string, label: string, value: string, isStatus?: boolean, href?: string }) {
  const content = (
    <>
      <div className="p-2.5 bg-surface-container-low rounded-lg border border-outline-variant/5 group-hover:border-outline-variant/20 transition-all shadow-inner">
        <span className="material-symbols-outlined text-outline text-lg">{icon}</span>
      </div>
      <div>
        <p className="text-[10px] font-black font-label text-outline uppercase tracking-widest mb-0.5">{label}</p>
        <div className="flex items-center gap-2">
          {isStatus && (
            <span className={`w-1.5 h-1.5 rounded-full ${
              value.toLowerCase() === 'approved' || value.toLowerCase() === 'active' 
                ? 'bg-tertiary shadow-[0_0_8px_#eac34a]' 
                : 'bg-outline/40'
            }`}></span>
          )}
          <p className="text-white font-bold text-sm">{value}</p>
        </div>
      </div>
    </>
  );

  if (href && href !== '#') {
    return (
      <a href={href} target="_blank" rel="noreferrer" className="flex items-center gap-4 group hover:bg-white/5 p-2 rounded-xl transition-all">
        {content}
      </a>
    );
  }

  return (
    <div className="flex items-center gap-4 group">
      {content}
    </div>
  );
}

function IntelligenceHome({ items, onSelect }: { items: IntelligenceItem[], onSelect: (id: number) => void }) {
  const recentItems = [...items].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()).slice(0, 4);

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-12 max-w-6xl mx-auto flex-1 flex flex-col"
    >
      <div className="mb-12">
        <h2 className="text-5xl font-black font-headline text-white tracking-tighter mb-4">Operational Intelligence</h2>
        <p className="text-outline text-lg font-body max-w-2xl">
          Strategic gateway to the Famiglia's proprietary dossiers and blueprints. Access the latest SITREP and research patterns curated by your AI agents.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        {/* Quick Stats/Summary Card */}
        <div className="p-8 bg-surface-container-low/50 rounded-2xl border border-outline-variant/10 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 blur-3xl group-hover:bg-primary/20 transition-all"></div>
          <span className="material-symbols-outlined text-4xl text-primary mb-6">description</span>
          <h3 className="text-2xl font-headline font-black text-white mb-2">Registry Overview</h3>
          <p className="text-on-surface-variant text-sm mb-8 leading-relaxed">
            Total of {items.length} active intelligence items tracked across the global network. Current system health is optimal.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-surface-container-lowest rounded-xl border border-outline-variant/5">
              <p className="text-[10px] font-black font-label text-outline uppercase tracking-widest mb-1">Approved</p>
              <p className="text-2xl font-headline font-black text-white">{items.filter(i => i.status?.toLowerCase() === 'approved').length}</p>
            </div>
            <div className="p-4 bg-surface-container-lowest rounded-xl border border-outline-variant/5">
              <p className="text-[10px] font-black font-label text-outline uppercase tracking-widest mb-1">In Review</p>
              <p className="text-2xl font-headline font-black text-white">{items.filter(i => i.status?.toLowerCase() === 'draft' || i.status?.toLowerCase() === 'pending').length}</p>
            </div>
          </div>
        </div>

        {/* System Directive Card */}
        <div className="p-8 bg-surface-container-low/50 rounded-2xl border border-outline-variant/10 relative overflow-hidden group border-l-4 border-l-tertiary">
          <span className="material-symbols-outlined text-4xl text-tertiary mb-6">shield</span>
          <h3 className="text-2xl font-headline font-black text-white mb-2">Protocol Zero</h3>
          <p className="text-on-surface-variant text-sm mb-8 leading-relaxed italic">
            "Knowledge is our most valuable asset. Access is restricted to Tier-1 operatives only. All interactions are logged and verified by the Rossini security layer."
          </p>
          <button className="px-6 py-2 bg-tertiary/10 hover:bg-tertiary/20 text-tertiary text-[10px] font-black font-label tracking-widest uppercase transition-all rounded-lg border border-tertiary/20">
            SECURITY MANIFESTO
          </button>
        </div>
      </div>

      <section>
        <h3 className="text-sm font-black font-label text-outline uppercase tracking-[0.2em] mb-6 flex items-center gap-3">
          Latest Reports
          <div className="h-[1px] flex-1 bg-outline-variant/10"></div>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recentItems.map((item, idx) => (
            <motion.div 
              key={item.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              onClick={() => onSelect(item.id)}
              className="p-4 bg-surface-container-low hover:bg-surface-container-high transition-all border border-outline-variant/5 rounded-xl flex items-center gap-4 cursor-pointer group"
            >
              <div className="w-12 h-12 bg-surface-container-lowest rounded-lg flex items-center justify-center border border-outline-variant/10 group-hover:border-primary/20 transition-all">
                <div className="text-xl transition-colors group-hover:text-primary">
                  {renderNotionIcon(item.icon) || (
                    <span className="material-symbols-outlined">
                      {item.item_type === 'dossier' ? 'folder_managed' : 'architecture'}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                <h4 className="text-white font-bold text-sm truncate">{item.title}</h4>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-[9px] font-label font-bold text-outline uppercase">{item.item_type}</span>
                  <span className="text-[9px] font-label font-bold text-tertiary uppercase bg-tertiary/5 px-1.5 rounded">{item.status}</span>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[8px] font-label text-outline uppercase block mb-1">Updated</span>
                <span className="text-[10px] font-bold text-white whitespace-nowrap">{new Date(item.updated_at).toLocaleDateString()}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </motion.div>
  );
}
