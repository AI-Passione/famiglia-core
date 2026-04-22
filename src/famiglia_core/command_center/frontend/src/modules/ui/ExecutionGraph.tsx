import { motion, AnimatePresence } from 'framer-motion';
import { useState, useMemo } from 'react';
import type { GraphDefinition } from '../../types';

interface ExecutionGraphProps {
  graph: GraphDefinition;
  activeNodeIds: string[];
  selectedNodeId: string | null;
  onNodeClick: (nodeId: string | null) => void;
}

export function ExecutionGraph({ graph, activeNodeIds, selectedNodeId, onNodeClick }: ExecutionGraphProps) {
  const [offsets, setOffsets] = useState<Record<string, { x: number, y: number }>>({});

  // Simple vertical layout for now: nodes are arranged in columns based on their dependencies
  // We'll calculate simple levels
  const levels: Record<string, number> = {};
  const processed = new Set<string>();
  
  // Start with entry nodes (START)
  levels["START"] = 0;
  processed.add("START");

  let changed = true;
  while (changed) {
    changed = false;
    graph.edges.forEach(edge => {
      if (processed.has(edge.source) && !processed.has(edge.target)) {
        levels[edge.target] = (levels[edge.source] || 0) + 1;
        processed.add(edge.target);
        changed = true;
      }
    });
  }

  // Group nodes by level
  const nodesByLevel: Record<number, string[]> = {};
  graph.nodes.forEach(node => {
    const level = levels[node.id] || 0;
    if (!nodesByLevel[level]) nodesByLevel[level] = [];
    nodesByLevel[level].push(node.id);
  });

  
  // Map node IDs to positions for edge drawing
  const LEVEL_HEIGHT = 140;
  const LEVEL_GAP = 60;
  const NODE_WIDTH = 180;
  
  const positions = useMemo(() => {
    const pos: Record<string, { x: number, y: number }> = {};
    const levels_arr = Object.entries(nodesByLevel).sort(([a], [b]) => Number(a) - Number(b));
    
    levels_arr.forEach(([_, nodeIds], lIdx) => {
      const totalWidth = nodeIds.length * NODE_WIDTH;
      nodeIds.forEach((nodeId, nIdx) => {
        const offset = offsets[nodeId] || { x: 0, y: 0 };
        pos[nodeId] = {
          x: (nIdx * NODE_WIDTH) - (totalWidth / 2) + (NODE_WIDTH / 2) + offset.x,
          y: lIdx * (LEVEL_HEIGHT + LEVEL_GAP) + 50 + offset.y
        };
      });
    });
    return pos;
  }, [graph, nodesByLevel, offsets]);

  const levels_arr = Object.entries(nodesByLevel).sort(([a], [b]) => Number(a) - Number(b));

  return (
    <div className="relative w-full overflow-x-auto py-10 min-h-[600px] flex justify-center">
      <div className="relative" style={{ width: '1200px', height: levels_arr.length * (LEVEL_HEIGHT + LEVEL_GAP) + 100 }}>
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="rgba(99, 102, 241, 0.5)" />
            </marker>
          </defs>
          
          {graph.edges.map((edge, idx) => {
            const start = positions[edge.source];
            const end = positions[edge.target];
            if (!start || !end) return null;

            // Use 600 as the horizontal center of our 1200px container
            const startX = 600 + start.x;
            const startY = start.y + 40; // Connect to bottom edge
            const endX = 600 + end.x;
            const endY = end.y - 40; // Connect to top edge
            
            const cp1Y = startY + 40;
            const cp2Y = endY - 40;

            const isHighlighted = activeNodeIds.includes(edge.source) && activeNodeIds.includes(edge.target);
            const midX = (startX + endX) / 2;
            const midY = (startY + endY) / 2;

            return (
              <g key={`${edge.source}-${edge.target}-${idx}`}>
                <motion.path
                  d={`M ${startX} ${startY} C ${startX} ${cp1Y}, ${endX} ${cp2Y}, ${endX} ${endY}`}
                  stroke={isHighlighted ? 'rgba(99, 102, 241, 0.8)' : 'rgba(255, 255, 255, 0.15)'}
                  strokeWidth={isHighlighted ? 2.5 : 1.5}
                  fill="none"
                  markerEnd="url(#arrowhead)"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 1, delay: idx * 0.05 }}
                />
                {edge.label && (
                  <foreignObject 
                    x={midX - 60} 
                    y={midY - 12} 
                    width="120" 
                    height="24"
                    className="pointer-events-none"
                  >
                    <div className="flex items-center justify-center h-full">
                      <span className="px-2 py-0.5 bg-[#1a1a1a]/90 border border-white/5 rounded text-[8px] font-mono text-outline uppercase tracking-tighter whitespace-nowrap">
                        {edge.label}
                      </span>
                    </div>
                  </foreignObject>
                )}
              </g>
            );
          })}
        </svg>

        {graph.nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const isActive = activeNodeIds.includes(node.id);
          const isEntry = node.type === 'entry';
          const isEnd = node.type === 'end';
          const isConditional = node.type === 'conditional';

          return (
            <motion.div
              key={node.id}
              onPan={(_, info) => {
                setOffsets(prev => ({
                  ...prev,
                  [node.id]: {
                    x: (prev[node.id]?.x || 0) + info.delta.x,
                    y: (prev[node.id]?.y || 0) + info.delta.y
                  }
                }));
              }}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => {
                onNodeClick(selectedNodeId === node.id ? null : node.id);
              }}
              style={{ 
                position: 'absolute', 
                left: `${600 + pos.x}px`, 
                top: pos.y,
                transform: 'translate(-50%, -50%)',
                touchAction: 'none',
                userSelect: 'none'
              }}
              className={`
                z-20 p-4 transition-colors cursor-pointer group
                ${isActive 
                  ? 'bg-primary/20 border-primary shadow-[0_0_20px_rgba(99,102,241,0.3)]' 
                  : 'bg-black/60 border-white/5 hover:border-white/20'}
                ${selectedNodeId === node.id ? 'ring-2 ring-primary ring-offset-4 ring-offset-background' : ''}
                ${isEntry || isEnd ? 'rounded-full px-8 py-3 border-2' : isConditional ? 'rotate-45 border-dashed' : 'rounded-lg border'}
                ${!isEntry && !isEnd ? 'min-w-[160px]' : ''}
              `}
            >
              <div className="flex flex-col items-center">
                {isEntry && <span className="material-symbols-outlined text-[10px] text-primary mb-1">play_arrow</span>}
                {isEnd && <span className="material-symbols-outlined text-[10px] text-rose-400 mb-1">stop</span>}
                <p className={`font-label text-[10px] uppercase tracking-widest ${isActive ? 'text-white' : 'text-outline group-hover:text-white/60'}`}>
                  {node.label}
                </p>
                {isActive && !isEntry && !isEnd && (
                  <div className="mt-2 flex space-x-1">
                    <motion.div className="w-1 h-1 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ repeat: Infinity, duration: 1 }} />
                    <motion.div className="w-1 h-1 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} />
                    <motion.div className="w-1 h-1 rounded-full bg-primary" animate={{ scale: [1, 1.5, 1] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} />
                  </div>
                )}
              </div>
              
              {isActive && (
                <motion.div 
                  className="absolute -inset-1 rounded-xl border border-primary/30"
                  animate={{ opacity: [0.3, 0.1, 0.3], scale: [1, 1.02, 1] }}
                  transition={{ duration: 3, repeat: Infinity }}
                />
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Node Detail Side Panel */}
      <AnimatePresence>
        {selectedNodeId && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            className="absolute right-0 top-0 bottom-0 w-80 bg-background/80 backdrop-blur-xl border-l border-outline-variant/10 z-50 overflow-y-auto p-6 shadow-[-10px_0_30px_rgba(0,0,0,0.5)]"
          >
            <div className="flex justify-between items-center mb-8">
              <h3 className="font-headline text-lg text-on-surface uppercase tracking-widest">Node Intel</h3>
              <button 
                onClick={() => onNodeClick(null)}
                className="p-2 hover:bg-white/5 rounded-full transition-colors"
              >
                <span className="material-symbols-outlined text-outline">close</span>
              </button>
            </div>

            {(() => {
              const node = graph.nodes.find(n => n.id === selectedNodeId);
              if (!node) return null;
              return (
                <div className="space-y-8">
                  <div className="space-y-2">
                    <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">Identity</p>
                    <h4 className="font-headline text-xl text-on-surface">{node.label}</h4>
                    <span className="inline-block px-2 py-0.5 rounded bg-white/5 font-mono text-[9px] text-outline uppercase">
                      ID: {node.id}
                    </span>
                  </div>

                  {node.description && (
                    <div className="space-y-3">
                      <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">Description</p>
                      <p className="font-body text-xs text-on-surface-variant leading-relaxed italic">
                        {node.description}
                      </p>
                    </div>
                  )}

                  {node.code && (
                    <div className="space-y-3">
                      <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">Operational Logic</p>
                      <div className="relative group">
                        <pre className="p-4 bg-black/40 rounded-xl border border-outline-variant/10 font-mono text-[10px] text-on-surface-variant overflow-x-auto leading-relaxed max-h-[400px]">
                          <code>{node.code}</code>
                        </pre>
                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                           <span className="text-[8px] font-mono text-outline uppercase bg-black/60 px-2 py-1 rounded">Python</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="pt-6 border-t border-outline-variant/10">
                     <p className="font-label text-[9px] text-outline uppercase tracking-widest mb-4">Node Context</p>
                     <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                           <p className="text-[8px] text-outline uppercase mb-1">Type</p>
                           <p className="text-xs text-on-surface capitalize">{node.type}</p>
                        </div>
                        <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                           <p className="text-[8px] text-outline uppercase mb-1">State</p>
                           <p className="text-xs text-on-surface">{activeNodeIds.includes(node.id) ? 'Active' : 'Idle'}</p>
                        </div>
                     </div>
                  </div>
                </div>
              );
            })()}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
