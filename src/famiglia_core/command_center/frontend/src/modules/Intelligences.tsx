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
      (item.title || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.content || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      Object.entries(item.properties || {}).some(([_, val]) => String(val).toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [items, searchQuery]);

  const marketResearches = filteredItems.filter(item => item.item_type === 'market_research');
  const prds = filteredItems.filter(item => item.item_type === 'prd');
  const projects = filteredItems.filter(item => item.item_type === 'project');
  const analysis = filteredItems.filter(item => item.item_type === 'analysis' || (!['market_research', 'prd', 'project'].includes(item.item_type || '')));

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
        <div className="p-4 border-b border-outline-variant/5 flex items-center justify-between gap-4">
          <a 
            href="/"
            className="flex items-center gap-2 text-[10px] font-black font-label text-outline hover:text-white transition-colors group"
          >
            <span className="material-symbols-outlined text-sm group-hover:-translate-x-1 transition-transform">arrow_back</span>
            COMMAND CENTER
          </a>
          <div className="flex-1 relative group">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm group-focus-within:text-primary transition-colors">search</span>
            <input 
              type="text" 
              placeholder="Filter..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface-container-low border border-outline-variant/10 rounded-lg py-1.5 pl-10 pr-4 text-[10px] text-white placeholder:text-outline focus:outline-none focus:border-primary/50 transition-all font-body uppercase tracking-tighter"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-6">
          {/* Market Researches Group */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between">
              <span className="text-[10px] font-black font-label text-outline uppercase tracking-widest">Market Researches</span>
              <span className="text-[10px] font-bold text-tertiary bg-tertiary/10 px-1.5 py-0.5 rounded">{marketResearches.length}</span>
            </div>
            <div className="space-y-1">
              {marketResearches.map(item => (
                <SidebarItem 
                  key={item.id}
                  item={item}
                  isSelected={selectedItemId === item.id}
                  onClick={() => setSelectedItemId(item.id)}
                />
              ))}
            </div>
          </div>

          {/* PRDs Group */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between">
              <span className="text-[10px] font-black font-label text-outline uppercase tracking-widest">PRDs</span>
              <span className="text-[10px] font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded">{prds.length}</span>
            </div>
            <div className="space-y-1">
              {prds.map(item => (
                <SidebarItem 
                  key={item.id}
                  item={item}
                  isSelected={selectedItemId === item.id}
                  onClick={() => setSelectedItemId(item.id)}
                />
              ))}
            </div>
          </div>
          
          {/* Projects Group */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between">
              <span className="text-[10px] font-black font-label text-outline uppercase tracking-widest">Projects</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(168, 85, 247, 0.1)', color: '#a855f7' }}>{projects.length}</span>
            </div>
            <div className="space-y-1">
              {projects.map(item => (
                <SidebarItem 
                  key={item.id}
                  item={item}
                  isSelected={selectedItemId === item.id}
                  onClick={() => setSelectedItemId(item.id)}
                />
              ))}
            </div>
          </div>
          
          {/* Analysis Group */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between">
              <span className="text-[10px] font-black font-label text-outline uppercase tracking-widest">Analysis</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', color: '#22c55e' }}>{analysis.length}</span>
            </div>
            <div className="space-y-1">
              {analysis.map(item => (
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
        </div>
      </div>

      {/* Main Content Viewport */}
      <div className="flex-1 overflow-y-auto custom-scrollbar relative flex flex-col">
        <AnimatePresence mode="wait">
          {selectedItem ? (
            <motion.div 
              key={selectedItem.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex"
            >
              <div className="flex-1 flex flex-col min-h-full">
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
                      {renderNotionIcon(selectedItem.icon) || (selectedItem.item_type === 'prd' ? '📑' : selectedItem.item_type === 'project' ? '🚀' : selectedItem.item_type === 'market_research' ? '📊' : '🔍')}
                    </div>
                    <div className="flex-1 pb-2">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="px-2 py-0.5 rounded bg-primary/20 text-primary text-[10px] font-black uppercase tracking-tighter border border-primary/30">
                          {selectedItem.item_type}
                        </span>
                        <span className="text-white/40 text-[10px] font-mono tracking-tighter uppercase">
                          {selectedItem.notion_id ? `NOTION ID: ${selectedItem.notion_id.substring(0, 8)}` : `LOCAL ID: ${selectedItem.id}`}
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
                  <PropertyItem 
                    icon="analytics" 
                    label="Status" 
                    value={selectedItem.status || 'Active'} 
                    isStatus 
                  />
                  <PropertyItem 
                    icon={selectedItem.notion_id ? "link" : "database"} 
                    label="Source" 
                    value={selectedItem.notion_id ? "Notion" : "AI Passion (Local)"} 
                    href={selectedItem.url || undefined} 
                  />
                  <PropertyItem 
                    icon="schedule" 
                    label="Created" 
                    value={new Date(selectedItem.created_time || selectedItem.created_at).toLocaleDateString(undefined, {
                      year: 'numeric', month: 'short', day: 'numeric'
                    })} 
                  />
                  <PropertyItem 
                    icon="history" 
                    label="Last Edited" 
                    value={new Date(selectedItem.last_edited_time || selectedItem.updated_at).toLocaleDateString(undefined, {
                      year: 'numeric', month: 'short', day: 'numeric'
                    })} 
                  />
                </div>

                {/* Content Area with TOC Sidebar optionally */}
                <div className="flex-1 flex relative">
                  <div className="flex-1 px-12 md:px-24 py-12 max-w-5xl mx-auto">
                    {/* Summary Callout */}
                    <div className="mb-12 p-6 bg-tertiary/5 rounded-xl border border-tertiary/20 flex gap-4">
                      <span className="material-symbols-outlined text-tertiary text-2xl">auto_awesome</span>
                      <div>
                        <span className="text-[10px] font-black font-label text-tertiary uppercase tracking-widest mb-1 block">AI-Generated Intelligence Summary</span>
                        <p className="text-sm text-on-surface-variant font-body leading-relaxed italic">
                          {selectedItem.summary || `This ${selectedItem.item_type?.replace('_', ' ')} focuses on ${(selectedItem.title || "this item").toLowerCase()}. Key patterns indicate significant market movement. Recommended action: Deep-dive into technical layer.`}
                        </p>
                      </div>
                    </div>

                    {/* Main Content Rendering */}
                    <div className="prose-container max-w-none font-body text-white/80 leading-relaxed mb-40">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({node, ...props}) => <h1 id={props.children?.toString().toLowerCase().replace(/\s+/g, '-')} className="markdown-h1" {...props} />,
                          h2: ({node, ...props}) => <h2 id={props.children?.toString().toLowerCase().replace(/\s+/g, '-')} className="markdown-h2" {...props} />,
                          h3: ({node, ...props}) => <h3 id={props.children?.toString().toLowerCase().replace(/\s+/g, '-')} className="markdown-h3" {...props} />,
                          p: ({node, ...props}) => <p className="markdown-p" {...props} />,
                          li: ({node, ...props}) => <li className="markdown-li" {...props} />,
                          ul: ({node, ...props}) => <ul className="markdown-ul" {...props} />,
                          ol: ({node, ...props}) => <ol className="markdown-ol" {...props} />,
                          code: ({node, ...props}) => <code className="markdown-code" {...props} />,
                          pre: ({node, ...props}) => <pre className="markdown-pre" {...props} />,
                          strong: ({node, ...props}) => <strong className="markdown-strong" {...props} />,
                          hr: () => <hr className="markdown-hr" />
                        }}
                      >
                        {selectedItem.content || ''}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {/* Table of Contents Side Pane */}
                  <TOC content={selectedItem.content || ''} />
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

        /* PREMIUM MARKDOWN STYLING */
        .prose-container {
          color: rgba(255, 255, 255, 0.85);
          line-height: 1.8;
          font-size: 1.05rem;
        }
        .markdown-h1 {
          font-family: 'Noto Serif', serif;
          font-size: 2.5rem;
          font-weight: 900;
          color: white;
          margin-top: 3rem;
          margin-bottom: 1.5rem;
          letter-spacing: -0.02em;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          padding-bottom: 0.5rem;
        }
        .markdown-h2 {
          font-family: 'Noto Serif', serif;
          font-size: 1.8rem;
          font-weight: 800;
          color: #ffb3b5; /* Primary accent */
          margin-top: 2.5rem;
          margin-bottom: 1rem;
          letter-spacing: -0.01em;
        }
        .markdown-h3 {
          font-family: 'Noto Serif', serif;
          font-size: 1.3rem;
          font-weight: 700;
          color: #eac34a; /* Tertiary accent */
          margin-top: 2rem;
          margin-bottom: 0.75rem;
        }
        .markdown-p {
          margin-bottom: 1.5rem;
        }
        .markdown-ul, .markdown-ol {
          margin-bottom: 1.5rem;
          padding-left: 1.5rem;
          list-style-type: square;
        }
        .markdown-li {
          margin-bottom: 0.5rem;
        }
        .markdown-strong {
          color: white;
          font-weight: 700;
        }
        .markdown-code {
          background: rgba(255, 255, 255, 0.05);
          padding: 0.2rem 0.4rem;
          border-radius: 4px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.9em;
          color: #ffb3b5;
        }
        .markdown-pre {
          background: #0e0e0e;
          padding: 1.5rem;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.05);
          overflow-x: auto;
          margin-bottom: 2rem;
        }
        .markdown-hr {
          border: 0;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          margin: 3rem 0;
        }

        @keyframes pulse-slow {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.6; }
        }
      `}} />
    </div>
  );
}

function TOC({ content }: { content: string }) {
  const headings = useMemo(() => {
    const lines = content.split('\n');
    const result: { id: string, text: string, level: number }[] = [];
    
    lines.forEach(line => {
      const match = line.match(/^(#{1,3})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const text = match[2].trim();
        const id = text.toLowerCase().replace(/\s+/g, '-');
        result.push({ id, text, level });
      }
    });
    
    return result;
  }, [content]);

  if (headings.length === 0) return null;

  return (
    <div className="hidden lg:block w-72 sticky top-0 h-screen overflow-y-auto p-8 border-l border-outline-variant/10 bg-surface-container-lowest/20 backdrop-blur-sm">
      <div className="flex items-center gap-2 mb-6 text-outline">
        <span className="material-symbols-outlined text-sm">segment</span>
        <span className="text-[10px] font-black font-label uppercase tracking-widest">Outline</span>
      </div>
      <nav className="space-y-1">
        {headings.map((h, i) => (
          <a 
            key={i}
            href={`#${h.id}`}
            className={`block text-[11px] font-medium transition-all hover:text-primary leading-tight py-1
              ${h.level === 1 ? 'text-white font-bold mt-4 border-b border-outline-variant/5 pb-1 mb-2' : ''}
              ${h.level === 2 ? 'pl-4 text-outline mb-1' : ''}
              ${h.level === 3 ? 'pl-8 text-outline/60' : ''}
            `}
          >
            {h.text}
          </a>
        ))}
      </nav>
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
            {item.item_type === 'prd' ? 'article' : item.item_type === 'project' ? 'rocket_launch' : item.item_type === 'market_research' ? 'query_stats' : 'search_insights'}
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
                      {item.item_type === 'prd' ? 'architecture' : item.item_type === 'project' ? 'rocket_launch' : item.item_type === 'market_research' ? 'query_stats' : 'search_insights'}
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
