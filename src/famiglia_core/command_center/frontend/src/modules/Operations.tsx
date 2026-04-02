import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition, MissionLogEntry, GraphNode, Task, PaginatedTasks } from '../types';
import { API_BASE } from '../config';

interface OperationsProps {
  graphs: GraphDefinition[];
  selectedGraph: GraphDefinition | null;
  setSelectedGraph: (g: GraphDefinition) => void;
  initialTasks: Task[];
}

export function Operations({ graphs, selectedGraph, setSelectedGraph, initialTasks }: OperationsProps) {
  const [logs, setLogs] = useState<MissionLogEntry[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [viewMode, setViewMode] = useState<'specific' | 'global'>('specific');
  const [systemTasks, setSystemTasks] = useState<Task[]>(initialTasks);
  const [totalTasks, setTotalTasks] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 10;

  const fetchLogs = useCallback(async () => {
    try {
      const endpoint = viewMode === 'specific' && selectedGraph 
        ? `${API_BASE}/mission-logs/${selectedGraph.id}` 
        : `${API_BASE}/mission-logs/all`;
      
      const res = await fetch(endpoint);
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (err) {
      console.error("Error fetching mission logs:", err);
    }
  }, [selectedGraph, viewMode]);

  const fetchSystemTasks = useCallback(async (page: number) => {
    try {
      const offset = (page - 1) * PAGE_SIZE;
      const res = await fetch(`${API_BASE}/tasks?limit=${PAGE_SIZE}&offset=${offset}`);
      if (res.ok) {
        const data = await res.json() as PaginatedTasks;
        setSystemTasks(data.tasks);
        setTotalTasks(data.total);
      }
    } catch (err) {
      console.error("Error fetching system tasks:", err);
    }
  }, []);

  // Initial fetch and view mode sync
  useEffect(() => {
    if (!selectedGraph && viewMode === 'specific') {
      setViewMode('global');
    }
    fetchLogs();
    fetchSystemTasks(currentPage);
  }, [fetchLogs, fetchSystemTasks, selectedGraph, viewMode, currentPage]);

  // Intelligent Polling: Refresh current page every 5s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchLogs();
      fetchSystemTasks(currentPage);
    }, 5000);
    return () => clearInterval(interval);
  }, [logs, fetchLogs, fetchSystemTasks, currentPage]);

  const handleExecute = async () => {
    if (!selectedGraph || isExecuting) return;
    
    setIsExecuting(true);
    try {
      const response = await fetch(`${API_BASE}/graphs/${selectedGraph.id}/execute`, {
        method: 'POST',
      });
      
      if (response.ok) {
        // Switch to specific view for the executed graph and refresh logs
        setViewMode('specific');
        setTimeout(fetchLogs, 1000);
      }
    } catch (err) {
      console.error("Error executing graph:", err);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-12"
    >
      <div className="space-y-8">
        <OperationsHeader selectedGraph={selectedGraph} viewMode={viewMode} setViewMode={setViewMode} />
        <GraphSelector 
          graphs={graphs} 
          selectedGraph={selectedGraph} 
          setSelectedGraph={(g) => {
            setSelectedGraph(g);
            setViewMode('specific');
          }} 
        />
      </div>
      
      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-12 space-y-12">
          {viewMode === 'specific' && selectedGraph ? (
            <GraphVisualizer graph={selectedGraph} onExecute={handleExecute} isExecuting={isExecuting} />
          ) : (
            <div className="bg-surface-container-low p-12 border border-outline-variant/10 text-center">
              <span className="material-symbols-outlined text-4xl text-outline/40 mb-4">analytics</span>
              <h3 className="font-headline text-xl text-on-surface">Global Operational View</h3>
              <p className="font-body text-sm text-outline max-w-md mx-auto mt-2">
                Select a specific Operational Graph from the tabs above to visualize its logic or initiate a new autonomous pipeline.
              </p>
            </div>
          )}
          <MissionLogs logs={logs} viewMode={viewMode} />
          
          <SystemTaskFeed 
            tasks={systemTasks} 
            total={totalTasks} 
            currentPage={currentPage} 
            setCurrentPage={setCurrentPage}
            pageSize={PAGE_SIZE}
          />
        </div>
      </div>
    </motion.div>
  );
}

function OperationsHeader({ 
  selectedGraph, 
  viewMode, 
  setViewMode 
}: { 
  selectedGraph: GraphDefinition | null;
  viewMode: 'specific' | 'global';
  setViewMode: (m: 'specific' | 'global') => void;
}) {
  return (
    <div className="flex justify-between items-end">
      <div>
        <h2 className="font-headline text-4xl text-on-surface mb-2 tracking-tight">
          {viewMode === 'global' ? 'Operational History' : `Operations: ${selectedGraph?.name}`}
        </h2>
        <p className="font-body text-[#a38b88] max-w-2xl text-sm leading-relaxed">
          {viewMode === 'global' 
            ? 'Unified execution stream for all autonomous pipelines across the project.'
            : `High-fidelity logic mapping for the '${selectedGraph?.name}' autonomous pipeline.`}
        </p>
      </div>
      <button 
        onClick={() => setViewMode(viewMode === 'global' ? 'specific' : 'global')}
        className={`px-4 py-2 border font-label text-[10px] uppercase tracking-widest transition-all ${
          viewMode === 'global' 
            ? 'bg-primary/10 text-primary border-primary/40' 
            : 'bg-surface-container-high/30 text-outline border-outline-variant/20 hover:text-on-surface hover:border-outline-variant/60'
        }`}
      >
        {viewMode === 'global' ? 'Back to Visualizer' : 'View Global History'}
      </button>
    </div>
  );
}

function GraphSelector({ graphs, selectedGraph, setSelectedGraph }: { 
  graphs: GraphDefinition[];
  selectedGraph: GraphDefinition | null;
  setSelectedGraph: (g: GraphDefinition) => void;
}) {
  const groups = useMemo(() => {
    const map: Record<string, GraphDefinition[]> = {};
    graphs.forEach(g => {
      const cat = g.category || "General";
      if (!map[cat]) map[cat] = [];
      map[cat].push(g);
    });
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [graphs]);

  return (
    <div className="space-y-6">
      {groups.map(([category, categoryGraphs]) => (
        <div key={category} className="space-y-3">
          <h4 className="font-label text-[10px] text-outline uppercase tracking-[0.2em] opacity-60">
            {category}
          </h4>
          <div className="flex flex-wrap gap-2">
            {categoryGraphs.map((graph) => {
              const isActive = selectedGraph?.id === graph.id;
              return (
                <button
                  key={graph.id}
                  onClick={() => setSelectedGraph(graph)}
                  className={`px-6 py-2 border transition-all duration-300 font-label text-[10px] uppercase tracking-widest ${
                    isActive 
                      ? 'bg-secondary/10 text-secondary border-secondary/50 shadow-[0_0_15px_rgba(234,195,74,0.1)]' 
                      : 'bg-surface-container-low/30 text-outline border-outline-variant/20 hover:border-outline-variant/50 hover:text-on-surface'
                  }`}
                >
                  {graph.name}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function GraphVisualizer({ graph, onExecute, isExecuting }: { 
  graph: GraphDefinition | null;
  onExecute: () => void;
  isExecuting: boolean;
}) {
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const positions = useMemo(() => {
    if (!graph) return {};
    
    const nodeLevels: Record<string, number> = {};
    const adjacency: Record<string, string[]> = {};
    graph.edges.forEach(e => {
      if (!adjacency[e.source]) adjacency[e.source] = [];
      adjacency[e.source].push(e.target);
    });

    const entryIds = graph.nodes.filter(n => n.type === 'entry').map(n => n.id);
    const queue = [...entryIds.map(id => ({ id, level: 0 }))];
    const visited = new Set<string>();

    while (queue.length > 0) {
      const { id, level } = queue.shift()!;
      if (visited.has(id)) continue;
      visited.add(id);
      
      if (nodeLevels[id] === undefined || level > nodeLevels[id]) {
        nodeLevels[id] = level;
      }
      
      (adjacency[id] || []).forEach(target => {
        if (!visited.has(target)) {
          queue.push({ id: target, level: level + 1 });
        }
      });
    }

    graph.nodes.forEach(n => {
      if (nodeLevels[n.id] === undefined) nodeLevels[n.id] = 0;
    });

    const levelGroups: Record<number, string[]> = {};
    Object.entries(nodeLevels).forEach(([id, level]) => {
      if (!levelGroups[level]) levelGroups[level] = [];
      levelGroups[level].push(id);
    });

    const pos: Record<string, { x: number, y: number }> = {};
    const Y_SPACING = 55;
    const X_SPACING = 110;
    const BASE_Y = 40;
    const CENTER_X = 300; // Increased SVG horizontal space

    Object.entries(levelGroups).forEach(([levelStr, ids]) => {
      const level = parseInt(levelStr);
      const y = BASE_Y + level * Y_SPACING;
      const totalWidth = (ids.length - 1) * X_SPACING;
      const startX = CENTER_X - totalWidth / 2;

      ids.sort().forEach((id, idx) => {
        pos[id] = { x: startX + idx * X_SPACING, y };
      });
    });

    return pos;
  }, [graph]);

  if (!graph) return null;

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
  };

  return (
    <section 
      className="bg-surface-container-low p-8 border border-outline-variant/10 relative group"
      onMouseMove={handleMouseMove}
    >
      <div className="flex justify-between items-center mb-10">
        <div>
          <h3 className="font-headline text-xl text-[#ffb3b5]">{graph.name} Visualizer</h3>
          <p className="font-label text-[10px] text-tertiary uppercase mt-1 tracking-widest opacity-80">Codified Graph // {graph.id}</p>
        </div>
        <div className="flex space-x-2">
          <span className="px-3 py-1 bg-surface-container-high text-on-surface-variant text-[10px] font-label uppercase tracking-tighter border border-outline-variant/10">Active Structure</span>
        </div>
      </div>

      {/* Dynamic SVG Flowchart Visualizer */}
      <div className="min-h-[480px] w-full bg-surface-container-lowest relative flex items-center justify-center border-b border-outline-variant/10 overflow-hidden p-4 cursor-crosshair">
        <svg className="w-full h-full opacity-80" viewBox="0 0 600 480" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="25" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#eac34a" />
            </marker>
          </defs>
          
          {graph.edges.map((edge, i) => {
            const p1 = positions[edge.source];
            const p2 = positions[edge.target];
            if (!p1 || !p2) return null;

            return (
              <g key={`edge-${i}`}>
                <path 
                  d={`M ${p1.x} ${p1.y} L ${p2.x} ${p2.y}`} 
                  stroke="#554240" 
                  strokeWidth="1.5" 
                  strokeDasharray={edge.label ? "4 4" : ""}
                  markerEnd="url(#arrowhead)"
                  className="transition-all duration-300 opacity-60 group-hover:opacity-100"
                />
                <circle r="2" fill="#eac34a" className="opacity-80">
                  <animateMotion dur={`${3 + i % 2}s`} repeatCount="indefinite" path={`M ${p1.x} ${p1.y} L ${p2.x} ${p2.y}`} />
                </circle>
              </g>
            );
          })}

          {graph.nodes.map((node) => {
            const pos = positions[node.id];
            if (!pos) return null;
            
            const isEntry = node.type === 'entry';
            const isEnd = node.type === 'end';
            const isHovered = hoveredNode?.id === node.id;

            return (
              <g 
                key={node.id} 
                className="cursor-pointer transition-all duration-300"
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
              >
                {isEntry || isEnd ? (
                  <circle 
                    cx={pos.x} cy={pos.y} r="8" 
                    fill="#1c1b1b" 
                    stroke="#ffb3b5" 
                    strokeWidth="2"
                    className={`${isHovered ? 'opacity-100 scale-110' : 'opacity-60'} transition-all`}
                  />
                ) : (
                  <rect 
                    x={pos.x - 50} y={pos.y - 15} width="100" height="30" 
                    fill="#1c1b1b" 
                    stroke={isHovered ? "#eac34a" : "#554240"}
                    strokeWidth={isHovered ? "2" : "1"}
                    rx="2"
                    className={`${isHovered ? 'shadow-[0_0_15px_rgba(234,195,74,0.2)]' : ''} transition-all`}
                  />
                )}
                <text 
                  x={pos.x} y={isEntry || isEnd ? pos.y + 25 : pos.y + 4} 
                  textAnchor="middle" 
                  fill={isEntry || isEnd ? "#ffb3b5" : "#eac34a"}
                  fontSize="8"
                  className={`tracking-widest uppercase font-bold transition-all ${isHovered ? 'opacity-100' : 'opacity-80'}`}
                  style={{ fontFamily: 'Space Grotesk' }}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Node Tooltip */}
        <AnimatePresence>
          {hoveredNode && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300, mass: 0.5 }}
              style={{
                position: 'absolute',
                left: mousePos.x,
                top: mousePos.y,
                zIndex: 50,
              }}
              className="bg-[#1c1b1b] p-3 border border-outline-variant/30 shadow-2xl min-w-[240px] pointer-events-none"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-label text-[8px] text-tertiary uppercase tracking-[0.2em] mb-1">
                      {hoveredNode.type === 'entry' ? 'Entry Node' : hoveredNode.type === 'end' ? 'Terminal' : 'Process Node'}
                    </p>
                    <h4 className="font-headline text-lg text-[#ffb3b5] leading-tight">{hoveredNode.label}</h4>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${hoveredNode.type === 'entry' ? 'bg-[#ffb3b5]' : 'bg-[#eac34a]'} animate-pulse shadow-[0_0_10px_rgba(234,195,74,0.3)]`}></div>
                </div>
                
                <div className="pt-4 border-t border-outline-variant/10">
                  <p className="font-body text-[#a38b88] text-[10px] leading-relaxed italic">
                    {`Autonomous execution unit for '${hoveredNode.label}' within the pipeline. Synchronizing state with Postgres checkpointer.`}
                  </p>
                </div>

                <div className="flex space-x-4 pt-2">
                  <div className="bg-surface-container-highest px-3 py-1 rounded-sm border border-outline-variant/10">
                    <p className="font-label text-[7px] text-on-surface-variant uppercase tracking-tighter">Latency</p>
                    <p className="font-body text-[10px] text-tertiary font-bold">12ms</p>
                  </div>
                  <div className="bg-surface-container-highest px-3 py-1 rounded-sm border border-outline-variant/10">
                    <p className="font-label text-[7px] text-on-surface-variant uppercase tracking-tighter">Reliability</p>
                    <p className="font-body text-[10px] text-primary font-bold">99.9%</p>
                  </div>
                </div>
              </div>
              
              {/* Decorative corner accents */}
              <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-tertiary/30"></div>
              <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-tertiary/30"></div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="absolute bottom-6 left-6 pointer-events-none">
          <div className="bg-surface-container-highest/40 backdrop-blur-sm px-4 py-1.5 border border-tertiary/10">
            <p className="font-label text-[8px] text-tertiary tracking-[0.2em] uppercase flex items-center">
              <span className="w-1.5 h-1.5 bg-tertiary rounded-full mr-2 animate-pulse"></span>
              Live Logic Topology // Connected
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <button 
          onClick={onExecute}
          disabled={isExecuting}
          className={`bg-[#4A0404] text-[#ffb3b5] px-10 py-3 font-bold text-xs uppercase tracking-[0.4em] transition-all active:scale-95 shadow-2xl border border-primary/20 ${
            isExecuting ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-125'
          }`}
        >
          {isExecuting ? 'DISPATCHING...' : 'EXECUTE GRAPH'}
        </button>
      </div>
    </section>
  );
}

function MissionLogs({ logs, viewMode }: { logs: MissionLogEntry[], viewMode: 'specific' | 'global' }) {
  return (
    <section className="bg-surface-container-low border border-outline-variant/10 overflow-hidden">
      <div className="p-8 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-high/30">
        <div>
          <h3 className="font-headline text-2xl text-on-surface">
            {viewMode === 'global' ? 'Global Command History' : 'Mission Logs'}
          </h3>
          <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-1 opacity-70">
            {viewMode === 'global' ? 'Across all Orchestration Features' : 'Operational Execution History'} // 0xAF
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
          <span className="font-label text-[10px] text-on-surface-variant uppercase tracking-widest">Live Stream</span>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-high/50 border-b border-outline-variant/10">
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">ID</th>
              {viewMode === 'global' && (
                <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Graph</th>
              )}
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Timestamp</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Status</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Duration</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Initiator</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-surface-container-highest/20 transition-colors group">
                <td className="px-8 py-5 font-mono text-[11px] text-tertiary">{log.id}</td>
                {viewMode === 'global' && (
                  <td className="px-8 py-5 font-label text-[10px] text-primary uppercase tracking-widest">
                    {log.graph_id}
                  </td>
                )}
                <td className="px-8 py-5 font-body text-xs text-on-surface-variant opacity-80">{log.timestamp}</td>
                <td className="px-8 py-5">
                  <span className={`px-3 py-1 text-[9px] font-label uppercase tracking-tighter border ${
                    log.status === 'success' 
                      ? 'bg-primary/10 text-primary border-primary/20' 
                      : log.status === 'running'
                      ? 'bg-secondary/10 text-secondary border-secondary/20 animate-pulse'
                      : 'bg-error/10 text-error border-error/20'
                  }`}>
                    {log.status === 'running' ? '● In Progress' : log.status}
                  </span>
                </td>
                <td className="px-8 py-5 font-body text-xs text-[#a38b88]">{log.duration}</td>
                <td className="px-8 py-5 font-label text-[10px] text-on-surface uppercase tracking-widest opacity-60 group-hover:opacity-100 transition-opacity">{log.initiator}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {logs.length === 0 && (
        <div className="p-20 text-center">
          <p className="font-label text-xs text-[#a38b88] uppercase tracking-[0.3em] animate-pulse">Awaiting connection to deep archives...</p>
        </div>
      )}
    </section>
  );
}

function SystemTaskFeed({ 
  tasks, 
  total, 
  currentPage, 
  setCurrentPage,
  pageSize 
}: { 
  tasks: Task[]; 
  total: number; 
  currentPage: number; 
  setCurrentPage: (p: number) => void;
  pageSize: number;
}) {
  const totalPages = Math.ceil(total / pageSize);

  return (
    <section className="bg-surface-container-low border border-outline-variant/10 overflow-hidden">
      <div className="p-8 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-high/30">
        <div>
          <h3 className="font-headline text-2xl text-on-surface">System Operations Feed</h3>
          <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-1 opacity-70">
            Raw Task Instance Stream // 0xDEEP
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="font-label text-[10px] text-outline uppercase tracking-widest">Page {currentPage} of {totalPages || 1}</span>
          </div>
          <div className="flex space-x-2">
            <button 
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="p-2 border border-outline-variant/20 hover:border-tertiary/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
            >
              <span className="material-symbols-outlined text-sm text-tertiary">chevron_left</span>
            </button>
            <button 
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage >= totalPages}
              className="p-2 border border-outline-variant/20 hover:border-tertiary/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
            >
              <span className="material-symbols-outlined text-sm text-tertiary">chevron_right</span>
            </button>
          </div>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-high/50 border-b border-outline-variant/10">
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">ID</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Title</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Payload</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Status</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Created At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {tasks.map((task) => (
              <tr key={task.id} className="hover:bg-surface-container-highest/20 transition-colors group">
                <td className="px-8 py-5 font-mono text-[11px] text-tertiary">T-{task.id}</td>
                <td className="px-8 py-5 font-body text-xs text-on-surface font-medium truncate max-w-[200px]">{task.title}</td>
                <td className="px-8 py-5">
                  <div className="flex items-center space-x-2 bg-surface-container-highest/40 px-3 py-1.5 border border-outline-variant/10 max-w-[300px]">
                    <span className="material-symbols-outlined text-[10px] text-outline/40">code</span>
                    <span className="font-mono text-[9px] text-[#a38b88] truncate">{task.task_payload}</span>
                  </div>
                </td>
                <td className="px-8 py-5">
                  <span className={`px-3 py-1 text-[9px] font-label uppercase tracking-tighter border ${
                    task.status === 'completed' 
                      ? 'bg-primary/10 text-primary border-primary/20' 
                      : task.status === 'in_progress'
                      ? 'bg-secondary/10 text-secondary border-secondary/20 animate-pulse'
                      : task.status === 'failed'
                      ? 'bg-error/10 text-error border-error/20'
                      : 'bg-surface-container-high text-outline border-outline-variant/10'
                  }`}>
                    {task.status}
                  </span>
                </td>
                <td className="px-8 py-5 font-mono text-[10px] text-[#a38b88] opacity-60 whitespace-nowrap">
                   {new Date(task.created_at).toLocaleString('en-US', { hour12: false, month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }).toUpperCase()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {tasks.length === 0 && (
        <div className="p-20 text-center">
          <p className="font-label text-xs text-[#a38b88] uppercase tracking-[0.3em] animate-pulse">Awaiting neural task signals...</p>
        </div>
      )}
    </section>
  );
}
