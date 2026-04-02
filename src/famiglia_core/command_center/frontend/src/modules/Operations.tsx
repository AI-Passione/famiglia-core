import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GraphDefinition, GraphNode, Task, PaginatedTasks, ActionLog, PaginatedActions, ConversationLog, PaginatedConversations } from '../types';
import { API_BASE } from '../config';

interface OperationsProps {
  graphs: GraphDefinition[];
  selectedGraph: GraphDefinition | null;
  setSelectedGraph: (g: GraphDefinition) => void;
  initialTasks: Task[];
}

export function Operations({ graphs, selectedGraph, setSelectedGraph, initialTasks }: OperationsProps) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [viewMode, setViewMode] = useState<'specific' | 'global'>('specific');

  // Agent Action Ledger State
  const [actions, setActions] = useState<ActionLog[]>([]);
  const [totalActions, setTotalActions] = useState(0);
  const [actionsPage, setActionsPage] = useState(1);
  const [selectedAgent, setSelectedAgent] = useState<string>('');

  // System Task Feed State (Mission Logs)
  const [missionLogs, setMissionLogs] = useState<Task[]>(initialTasks);
  const [totalMissionLogs, setTotalMissionLogs] = useState(0);
  const [missionLogsPage, setMissionLogsPage] = useState(1);

  // Strategic Dialogue State
  const [conversations, setConversations] = useState<ConversationLog[]>([]);
  const [totalConversations, setTotalConversations] = useState(0);
  const [conversationsPage, setConversationsPage] = useState(1);

  const PAGE_SIZE = 10;

  const fetchActions = useCallback(async (page: number, agent?: string) => {
    try {
      const offset = (page - 1) * PAGE_SIZE;
      let url = `${API_BASE}/actions?limit=${PAGE_SIZE}&offset=${offset}`;
      if (agent) url += `&agent_name=${encodeURIComponent(agent)}`;

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json() as PaginatedActions;
        setActions(data.actions);
        setTotalActions(data.total);
      }
    } catch (err) {
      console.error("Error fetching agent actions:", err);
    }
  }, []);

  const fetchMissionLogs = useCallback(async (page: number) => {
    try {
      const offset = (page - 1) * PAGE_SIZE;
      const res = await fetch(`${API_BASE}/tasks?limit=${PAGE_SIZE}&offset=${offset}`);
      if (res.ok) {
        const data = await res.json() as PaginatedTasks;
        setMissionLogs(data.tasks);
        setTotalMissionLogs(data.total);
      }
    } catch (err) {
      console.error("Error fetching mission logs:", err);
    }
  }, []);

  const fetchConversations = useCallback(async (page: number) => {
    try {
      const offset = (page - 1) * PAGE_SIZE;
      const res = await fetch(`${API_BASE}/conversations?limit=${PAGE_SIZE}&offset=${offset}`);
      if (res.ok) {
        const data = await res.json() as PaginatedConversations;
        setConversations(data.conversations);
        setTotalConversations(data.total);
      }
    } catch (err) {
      console.error("Error fetching conversations:", err);
    }
  }, []);

  // Initial fetch and view mode sync
  useEffect(() => {
    if (!selectedGraph && viewMode === 'specific') {
      setViewMode('global');
    }
    fetchActions(actionsPage, selectedAgent);
    fetchMissionLogs(missionLogsPage);
    fetchConversations(conversationsPage);
  }, [fetchActions, fetchMissionLogs, fetchConversations, selectedGraph, viewMode, actionsPage, missionLogsPage, conversationsPage, selectedAgent]);

  // Intelligent Polling: Refresh all feeds every 5s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchActions(actionsPage, selectedAgent);
      fetchMissionLogs(missionLogsPage);
      fetchConversations(conversationsPage);
    }, 5000);
    return () => clearInterval(interval);
  }, [actionsPage, missionLogsPage, conversationsPage, selectedAgent, fetchActions, fetchMissionLogs, fetchConversations]);

  const handleExecute = async () => {
    if (!selectedGraph || isExecuting) return;

    setIsExecuting(true);
    try {
      const response = await fetch(`${API_BASE}/graphs/${selectedGraph.id}/execute`, {
        method: 'POST',
      });

      if (response.ok) {
        setViewMode('specific');
        setTimeout(() => fetchMissionLogs(1), 1000);
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
        <OperationsHeader selectedGraph={selectedGraph} viewMode={viewMode} />
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
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-surface-container-low p-8 border border-outline-variant/10 text-center space-y-2">
                <span className="material-symbols-outlined text-3xl text-tertiary mb-2">assignment</span>
                <h4 className="font-label text-[10px] text-outline uppercase tracking-widest">Neural Mission Logs</h4>
                <p className="font-headline text-4xl text-on-surface">{totalMissionLogs}</p>
                <div className="h-1 w-12 bg-tertiary/30 mx-auto rounded-full"></div>
              </div>
              <div className="bg-surface-container-low p-8 border border-outline-variant/10 text-center space-y-2">
                <span className="material-symbols-outlined text-3xl text-secondary mb-2">forum</span>
                <h4 className="font-label text-[10px] text-outline uppercase tracking-widest">Strategic Dialogues</h4>
                <p className="font-headline text-4xl text-on-surface">{totalConversations}</p>
                <div className="h-1 w-12 bg-secondary/30 mx-auto rounded-full"></div>
              </div>
              <div className="bg-surface-container-low p-8 border border-outline-variant/10 text-center space-y-2">
                <span className="material-symbols-outlined text-3xl text-primary mb-2">construction</span>
                <h4 className="font-label text-[10px] text-outline uppercase tracking-widest">Tool Executions</h4>
                <p className="font-headline text-4xl text-on-surface">{totalActions}</p>
                <div className="h-1 w-12 bg-primary/30 mx-auto rounded-full"></div>
              </div>
            </div>
          )}

          <MissionLogFeed
            tasks={missionLogs}
            total={totalMissionLogs}
            currentPage={missionLogsPage}
            setCurrentPage={setMissionLogsPage}
            pageSize={PAGE_SIZE}
          />

          <StrategicDialogue
            conversations={conversations}
            total={totalConversations}
            currentPage={conversationsPage}
            setCurrentPage={setConversationsPage}
            pageSize={PAGE_SIZE}
          />

          <AgentActionLedger
            actions={actions}
            total={totalActions}
            currentPage={actionsPage}
            setCurrentPage={setActionsPage}
            pageSize={PAGE_SIZE}
            selectedAgent={selectedAgent}
            setSelectedAgent={setSelectedAgent}
          />
        </div>
      </div>
    </motion.div>
  );
}

function OperationsHeader({
  selectedGraph,
  viewMode,
}: {
  selectedGraph: GraphDefinition | null;
  viewMode: 'specific' | 'global';
}) {
  return (
    <div className="flex justify-between items-end">
      <div>
        <h2 className="font-headline text-4xl text-on-surface mb-2 tracking-tight">
          {viewMode === 'global' ? 'Operations' : `Operations: ${selectedGraph?.name}`}
        </h2>
        <p className="font-body text-[#a38b88] max-w-2xl text-sm leading-relaxed">
          {viewMode === 'global'
            ? 'Unified execution stream for all autonomous pipelines across the project.'
            : `High-fidelity logic mapping for the '${selectedGraph?.name}' autonomous pipeline.`}
        </p>
      </div>
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
                  className={`px-6 py-2 border transition-all duration-300 font-label text-[10px] uppercase tracking-widest ${isActive
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

function AgentActionLedger({
  actions,
  total,
  currentPage,
  setCurrentPage,
  pageSize,
  selectedAgent,
  setSelectedAgent
}: {
  actions: ActionLog[];
  total: number;
  currentPage: number;
  setCurrentPage: (p: number) => void;
  pageSize: number;
  selectedAgent: string;
  setSelectedAgent: (a: string) => void;
}) {
  const totalPages = Math.ceil(total / pageSize);
  const AGENTS = ["Alfredo", "Vito", "Riccado", "Rossini", "Tommy", "Bella", "Kowalski"];

  return (
    <section className="bg-surface-container-low border border-outline-variant/10 overflow-hidden">
      <div className="p-8 border-b border-outline-variant/10 flex justify-between items-center bg-surface-container-high/30">
        <div>
          <h3 className="font-headline text-2xl text-on-surface">Tool Action Ledger</h3>
          <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-1 opacity-70">
            Granular Mechanical Execution Stream // 0xTOOL
          </p>
        </div>
        <div className="flex items-center space-x-6">
          {/* Agent Filter */}
          <div className="flex items-center space-x-3">
            <span className="font-label text-[9px] text-outline uppercase tracking-widest">Filter:</span>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="bg-surface-container-highest border border-outline-variant/20 text-on-surface font-label text-[10px] uppercase px-3 py-1.5 focus:outline-none focus:border-primary/40"
            >
              <option value="">All Agents</option>
              {AGENTS.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-4">
            <span className="font-label text-[10px] text-outline uppercase tracking-widest">Page {currentPage} of {totalPages || 1}</span>
            <div className="flex space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="p-2 border border-outline-variant/20 hover:border-primary/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
              >
                <span className="material-symbols-outlined text-sm text-primary">chevron_left</span>
              </button>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage >= totalPages}
                className="p-2 border border-outline-variant/20 hover:border-primary/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
              >
                <span className="material-symbols-outlined text-sm text-primary">chevron_right</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-high/50 border-b border-outline-variant/10">
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">ID</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Timestamp</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Agent</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Action</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Details</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {actions?.map((action) => (
              <tr key={action.id} className="hover:bg-surface-container-highest/20 transition-colors group">
                <td className="px-8 py-5 font-mono text-[11px] text-tertiary">{action.id}</td>
                <td className="px-8 py-5 font-mono text-[10px] text-[#a38b88] opacity-60">
                  {new Date(action.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </td>
                <td className="px-8 py-5 font-label text-[10px] text-primary uppercase tracking-widest font-bold">
                  {action.agent_name}
                </td>
                <td className="px-8 py-5">
                  <span className="bg-surface-container-highest px-3 py-1 rounded-sm border border-outline-variant/10 font-mono text-[10px] text-on-surface">
                    {action.action_type}
                  </span>
                </td>
                <td className="px-8 py-5">
                  <div className="flex items-center space-x-2 bg-surface-container-highest/40 px-3 py-1.5 border border-outline-variant/10 max-w-[300px]">
                    <span className="material-symbols-outlined text-[10px] text-outline/40">data_object</span>
                    <span className="font-mono text-[9px] text-[#a38b88] truncate">
                      {JSON.stringify(action.action_details || {})}
                    </span>
                  </div>
                </td>
                <td className="px-8 py-5">
                  <span className={`px-3 py-1 text-[9px] font-label uppercase tracking-tighter border ${action.approval_status === 'APPROVED'
                      ? 'bg-primary/10 text-primary border-primary/20'
                      : action.completed_at
                        ? 'bg-secondary/10 text-secondary border-secondary/20'
                        : 'bg-surface-container-high text-outline border-outline-variant/10'
                    }`}>
                    {action.approval_status || (action.completed_at ? "COMPLETE" : "ACTIVE")}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {actions.length === 0 && (
        <div className="p-20 text-center">
          <p className="font-label text-xs text-[#a38b88] uppercase tracking-[0.3em] animate-pulse">Awaiting granular action signals...</p>
        </div>
      )}
    </section>
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
    const CENTER_X = 300;

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
          className={`bg-[#4A0404] text-[#ffb3b5] px-10 py-3 font-bold text-xs uppercase tracking-[0.4em] transition-all active:scale-95 shadow-2xl border border-primary/20 ${isExecuting ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-125'
            }`}
        >
          {isExecuting ? 'DISPATCHING...' : 'EXECUTE GRAPH'}
        </button>
      </div>
    </section>
  );
}

function MissionLogFeed({
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
          <h3 className="font-headline text-2xl text-on-surface">Mission Logs</h3>
          <p className="font-label text-[10px] text-tertiary uppercase tracking-[0.2em] mt-1 opacity-70">
            Autonomous Neural Trajectory // 0xDEEP
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
            {tasks?.map((task) => (
              <tr key={task.id} className="hover:bg-surface-container-highest/20 transition-colors group">
                <td className="px-8 py-5 font-mono text-[11px] text-tertiary">{task.id}</td>
                <td className="px-8 py-5 font-body text-xs text-on-surface font-medium truncate max-w-[200px]">{task.title}</td>
                <td className="px-8 py-5">
                  <div className="flex items-center space-x-2 bg-surface-container-highest/40 px-3 py-1.5 border border-outline-variant/10 max-w-[300px]">
                    <span className="material-symbols-outlined text-[10px] text-outline/40">code</span>
                    <span className="font-mono text-[9px] text-[#a38b88] truncate">{task.task_payload}</span>
                  </div>
                </td>
                <td className="px-8 py-5">
                  <span className={`px-3 py-1 text-[9px] font-label uppercase tracking-tighter border ${task.status === 'completed'
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
          <p className="font-label text-xs text-[#a38b88] uppercase tracking-[0.3em] animate-pulse">Awaiting neural mission signals...</p>
        </div>
      )}
    </section>
  );
}

function StrategicDialogue({
  conversations,
  total,
  currentPage,
  setCurrentPage,
  pageSize
}: {
  conversations: ConversationLog[];
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
          <h3 className="font-headline text-2xl text-on-surface">Strategic Dialogue</h3>
          <p className="font-label text-[10px] text-secondary uppercase tracking-[0.2em] mt-1 opacity-70">
            Agent Intelligence Ledger // 0xCHAT
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
              className="p-2 border border-outline-variant/20 hover:border-secondary/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
            >
              <span className="material-symbols-outlined text-sm text-secondary">chevron_left</span>
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage >= totalPages}
              className="p-2 border border-outline-variant/20 hover:border-secondary/40 disabled:opacity-30 disabled:pointer-events-none transition-all"
            >
              <span className="material-symbols-outlined text-sm text-secondary">chevron_right</span>
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-surface-container-high/50 border-b border-outline-variant/10">
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">ID</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Conversation Key</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Lead Agent</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Latest Snippet</th>
              <th className="px-8 py-4 font-label text-[10px] text-[#a38b88] uppercase tracking-widest whitespace-nowrap">Updated At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {conversations?.map((conv) => (
              <tr key={conv.id} className="hover:bg-surface-container-highest/20 transition-colors group">
                <td className="px-8 py-5 font-mono text-[11px] text-secondary">{conv.id}</td>
                <td className="px-8 py-5 font-label text-[10px] text-on-surface uppercase tracking-widest">{conv.conversation_key}</td>
                <td className="px-8 py-5 font-label text-[10px] text-secondary uppercase tracking-widest font-bold">
                  {conv.latest_agent || "Anonymous"}
                </td>
                <td className="px-8 py-5">
                  <div className="flex items-center space-x-2 bg-surface-container-highest/40 px-3 py-1.5 border border-outline-variant/10 max-w-[400px]">
                    <span className="material-symbols-outlined text-[10px] text-outline/40">forum</span>
                    <p className="font-body text-[10px] text-[#a38b88] truncate italic">
                      "{conv.latest_message || "Awaiting strategy exchange..."}"
                    </p>
                  </div>
                </td>
                <td className="px-8 py-5 font-mono text-[10px] text-[#a38b88] opacity-60 whitespace-nowrap">
                  {new Date(conv.updated_at).toLocaleString('en-US', { hour12: false, month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }).toUpperCase()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {conversations.length === 0 && (
        <div className="p-20 text-center">
          <p className="font-label text-xs text-[#a38b88] uppercase tracking-[0.3em] animate-pulse">Awaiting strategic verbal signals...</p>
        </div>
      )}
    </section>
  );
}
