import { motion, AnimatePresence } from 'framer-motion';
import type { Action } from '../../types';
import { useTerminal } from '../TerminalContext';

const AGENT_TO_CHANNEL: Record<string, string> = {
  alfredo: 'command-center',
  riccardo: 'tech',
  rossini: 'product',
  bella: 'admin',
  kowalski: 'analytics',
  giuseppina: 'social',
  tommy: 'lounge',
  vito: 'alerts'
};

interface FeedItemProps {
  action: Action;
  priority: boolean;
}

function FeedItem({ action, priority }: FeedItemProps) {
  const { setActiveChatId, setTerminalOpen } = useTerminal();
  const time = new Date(action.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  
  const handleRespond = () => {
    const channelId = AGENT_TO_CHANNEL[action.agent_name.toLowerCase()] || 'command-center';
    setActiveChatId(channelId);
    setTerminalOpen(true);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: 20 }} 
      animate={{ opacity: 1, x: 0 }} 
      className={`flex gap-4 items-start group relative ${!priority ? 'opacity-70 hover:opacity-100' : ''} transition-opacity`}
    >
      <div className={`${priority ? 'bg-[#4A0404]' : 'bg-surface-container-highest'} p-2 rounded-sm shrink-0 shadow-sm transition-transform group-hover:scale-110`}>
        <span className={`material-symbols-outlined text-xs ${priority ? 'text-white' : 'text-secondary'}`}>
          {priority ? 'priority_high' : 'info'}
        </span>
      </div>
      <div className="flex-1">
        <div className="flex justify-between items-start">
          <p className={`font-label text-[10px] ${priority ? 'text-tertiary' : 'text-outline'}`}>{time}</p>
          <button 
            onClick={handleRespond}
            className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[9px] uppercase tracking-tighter font-bold text-primary hover:text-white"
          >
            Respond <span className="material-symbols-outlined text-[10px]">chat</span>
          </button>
        </div>
        <p className={`text-sm font-body ${priority ? 'text-on-surface' : 'text-on-surface-variant'} leading-snug`}>
          <span className="font-bold capitalize">{action.agent_name}:</span> {action.action_type.replace(/_/g, ' ')}
        </p>
      </div>
    </motion.div>
  );
}

interface IntelligenceFeedProps {
  actions: Action[];
}

export function IntelligenceFeed({ actions }: IntelligenceFeedProps) {
  return (
    <div className="col-span-12 lg:col-span-4 space-y-6">
      <div className="bg-surface-container-low p-6 h-full flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-headline text-xl text-on-surface">Intelligence Feed</h3>
          <span className="material-symbols-outlined text-outline">sensors</span>
        </div>
        <div className="flex-1 space-y-6 overflow-y-auto pr-2 custom-scrollbar">
          <AnimatePresence>
            {actions.map((action, idx) => (
              <FeedItem key={action.id} action={action} priority={idx === 0 || idx === 3} />
            ))}
          </AnimatePresence>
          {actions.length === 0 && <p className="font-label text-xs text-outline text-center py-10">No recent intelligence.</p>}
        </div>
        <button className="mt-6 w-full py-2 border border-outline/20 font-label text-[10px] uppercase tracking-widest text-outline hover:text-primary hover:border-primary/50 transition-all">
          View Archives
        </button>
      </div>
    </div>
  );
}
