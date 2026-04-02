import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition, MissionLogEntry, GraphNode } from '../types';
import { API_BASE } from '../config';

interface SOPProps {
  graphs: GraphDefinition[];
  selectedGraph: GraphDefinition | null;
  setSelectedGraph: (g: GraphDefinition) => void;
}

export function SOP({ graphs, selectedGraph, setSelectedGraph }: SOPProps) {
  const [logs, setLogs] = useState<MissionLogEntry[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);

  const fetchLogs = useCallback(() => {
    if (selectedGraph) {
      fetch(`${API_BASE}/mission-logs/${selectedGraph.id}`)
        .then(res => res.json())
        .then(data => setLogs(data))
        .catch(err => console.error("Error fetching mission logs:", err));
    }
  }, [selectedGraph]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleExecute = async () => {
    if (!selectedGraph || isExecuting) return;
    
    setIsExecuting(true);
    try {
      const response = await fetch(`${API_BASE}/graphs/${selectedGraph.id}/execute`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (response.ok) {
        // Optimistically add a "running" log entry or just refresh
        setTimeout(fetchLogs, 1000);
      } else {
        console.error("Execution failed:", data.detail);
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
        <SOPHeader selectedGraph={selectedGraph} />
        <GraphSelector graphs={graphs} selectedGraph={selectedGraph} setSelectedGraph={setSelectedGraph} />
      </div>
      
      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-12 space-y-12">
          <GraphVisualizer graph={selectedGraph} onExecute={handleExecute} isExecuting={isExecuting} />
          <MissionLogs logs={logs} />
        </div>
      </div>
    </motion.div>
  );
}

function SOPHeader({ selectedGraph }: { selectedGraph: GraphDefinition | null }) {
  return (
    <div>
      <h2 className="font-headline text-4xl text-on-surface mb-2 tracking-tight">
        SOP: {selectedGraph ? selectedGraph.name : 'Standard Operation Procedure'}
      </h2>
      <p className="font-body text-[#a38b88] max-w-2xl text-sm leading-relaxed">
        {selectedGraph 
          ? `High-fidelity logic mapping for the '${selectedGraph.name}' autonomous pipeline.`
          : 'High-fidelity logic mapping and autonomous pipeline orchestration for the Famiglia\'s digital assets.'}
      </p>
    </div>
  );
}

function GraphSelector({ graphs, selectedGraph, setSelectedGraph }: { 
  graphs: GraphDefinition[];
  selectedGraph: GraphDefinition | null;
  setSelectedGraph: (g: GraphDefinition) => void;
}) {
  const categories = [
    {
      name: "Market Research",
      ids: ["market_research"]
    },
    {
      name: "Product Development",
      ids: ["prd_drafting", "prd_review", "milestone_creation", "grooming", "code_implementation"]
    }
  ];

  return (
    <div className="space-y-6">
      {categories.map((category) => {
        const categoryGraphs = category.ids
          .map(id => graphs.find(g => g.id === id))
          .filter((g): g is GraphDefinition => !!g);
        if (categoryGraphs.length === 0) return null;

        return (
          <div key={category.name} className="space-y-3">
            <h4 className="font-label text-[10px] text-outline uppercase tracking-[0.2em] opacity-60">
              {category.name}
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
        );
      })}
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

function MissionLogs({ logs }: { logs: MissionLogEntry[] }) {
  return (
    <section className="bg-surface-container-low border border-outline-variant/10 overflow-hidden">
      <div className="p-8 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-high/30">
        <div>
          <h3 className="font-headline text-2xl text-on-surface">Mission Logs</h3>
          <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-1 opacity-70">Operational Execution History // 0xAF</p>
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
