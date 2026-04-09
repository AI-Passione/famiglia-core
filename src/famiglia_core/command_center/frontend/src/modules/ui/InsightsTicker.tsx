import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_BASE } from '../../config';
import type { InsightSummary } from '../../types';

export function InsightsTicker() {
  const [insights, setInsights] = useState<InsightSummary[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const res = await fetch(`${API_BASE}/insights?limit=10`);
        if (res.ok) {
          const data = await res.json();
          setInsights(data);
        }
      } catch (err) {
        console.error('Failed to fetch insights', err);
      }
    };
    fetchInsights();
    const interval = setInterval(fetchInsights, 60000); // refresh every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (insights.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % Math.max(1, insights.length));
    }, 5000); // slide every 5 seconds
    return () => clearInterval(timer);
  }, [insights.length]);

  return (
    <div className="bg-surface-container-low p-6 flex flex-col justify-center relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-30">
        <span className="material-symbols-outlined text-[48px]">moving</span>
      </div>
      <div className="flex items-center gap-2 mb-2 relative z-10">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        <h3 className="font-label text-[10px] uppercase tracking-widest text-outline">Market & Intel Pulse</h3>
      </div>
      
      <div className="h-[80px] relative mt-2 z-10">
        {insights.length > 0 ? (
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
              className="absolute inset-0"
            >
              <h4 className="font-headline text-lg text-on-surface line-clamp-1 mb-1">
                {insights[currentIndex]?.title || 'Insight Unavailable'}
              </h4>
              <p className="font-body text-sm text-on-surface-variant line-clamp-2 italic opacity-80">
                "{insights[currentIndex]?.rossini_tldr || 'Analyzing latest signals...'}"
              </p>
            </motion.div>
          </AnimatePresence>
        ) : (
          <div className="flex items-center gap-2 text-outline-variant h-full">
            <span className="material-symbols-outlined animate-spin text-[16px]">refresh</span>
            <span className="font-body text-sm uppercase tracking-widest text-[10px]">Awaiting Intel...</span>
          </div>
        )}
      </div>
    </div>
  );
}
