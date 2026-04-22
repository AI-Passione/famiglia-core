import { motion } from 'framer-motion';
import type { GraphDefinition } from '../../types';

interface ExecutionGraphProps {
  graph: GraphDefinition;
  activeNodeIds: string[];
  selectedNodeId: string | null;
  onNodeClick: (nodeId: string | null) => void;
}

export function ExecutionGraph({ graph, activeNodeIds, selectedNodeId, onNodeClick }: ExecutionGraphProps) {
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
  const LEVEL_HEIGHT = 120;
  const LEVEL_GAP = 60;
  const NODE_WIDTH = 180;
  
  const positions: Record<string, { x: number, y: number }> = {};
  const levels_arr = Object.entries(nodesByLevel).sort(([a], [b]) => Number(a) - Number(b));
  
  levels_arr.forEach(([_, nodeIds], lIdx) => {
    const totalWidth = nodeIds.length * NODE_WIDTH;
    nodeIds.forEach((nodeId, nIdx) => {
      positions[nodeId] = {
        x: (nIdx * NODE_WIDTH) - (totalWidth / 2) + (NODE_WIDTH / 2),
        y: lIdx * (LEVEL_HEIGHT + LEVEL_GAP) + 50
      };
    });
  });

  return (
    <div className="relative w-full overflow-x-auto py-10 min-h-[500px] flex flex-col items-center">
      <div className="relative" style={{ width: '100%', height: levels_arr.length * (LEVEL_HEIGHT + LEVEL_GAP) + 100 }}>
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minWidth: 800 }}>
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="rgba(99, 102, 241, 0.3)" />
            </marker>
          </defs>
          
          {graph.edges.map((edge, idx) => {
            const start = positions[edge.source];
            const end = positions[edge.target];
            if (!start || !end) return null;

            // Draw a curved path from bottom of start to top of end
            const startX = 400 + start.x; // Offset to center
            const startY = start.y + 20;
            const endX = 400 + end.x;
            const endY = end.y - 20;
            
            const cp1Y = startY + 40;
            const cp2Y = endY - 40;

            const isHighlighted = activeNodeIds.includes(edge.source) && activeNodeIds.includes(edge.target);

            return (
              <motion.path
                key={`${edge.source}-${edge.target}-${idx}`}
                d={`M ${startX} ${startY} C ${startX} ${cp1Y}, ${endX} ${cp2Y}, ${endX} ${endY}`}
                stroke={isHighlighted ? 'rgba(99, 102, 241, 0.6)' : 'rgba(255, 255, 255, 0.1)'}
                strokeWidth={isHighlighted ? 2 : 1}
                fill="none"
                markerEnd="url(#arrowhead)"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.5, delay: idx * 0.1 }}
              />
            );
          })}
        </svg>

        {graph.nodes.map((node) => {
          const pos = positions[node.id];
          if (!pos) return null;
          const isActive = activeNodeIds.includes(node.id);
          const isEntry = node.type === 'entry';
          const isEnd = node.type === 'end';

          return (
            <motion.div
              key={node.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={() => onNodeClick(selectedNodeId === node.id ? null : node.id)}
              style={{ 
                position: 'absolute', 
                left: `calc(50% + ${pos.x}px)`, 
                top: pos.y,
                transform: 'translate(-50%, -50%)'
              }}
              className={`
                z-20 p-4 rounded-xl border text-center transition-all cursor-pointer group
                ${isActive 
                  ? 'bg-primary/20 border-primary shadow-[0_0_20px_rgba(99,102,241,0.3)]' 
                  : 'bg-black/60 border-white/5 hover:border-white/20'}
                ${selectedNodeId === node.id ? 'ring-2 ring-primary ring-offset-4 ring-offset-background' : ''}
                ${isEntry || isEnd ? 'rounded-full px-6 py-2' : 'min-w-[150px]'}
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
    </div>
  );
}
