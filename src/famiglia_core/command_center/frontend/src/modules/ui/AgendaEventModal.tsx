import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { FamigliaAgent, GraphDefinition, AgendaEntry } from '../../types';
import { API_BASE } from '../../config';
import { useToast } from './ToastProvider';

interface AgendaEventModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  agents: FamigliaAgent[];
  graphs: GraphDefinition[];
  initialEntry?: AgendaEntry | null;
  initialDate?: Date | null;
}

export function AgendaEventModal({
  isOpen,
  onClose,
  onSuccess,
  agents,
  graphs,
  initialEntry,
  initialDate,
}: AgendaEventModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [priority, setPriority] = useState('medium');
  const [selectedGraphId, setSelectedGraphId] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const { showToast } = useToast();

  const isEdit = !!initialEntry;

  useEffect(() => {
    if (initialEntry) {
      setTitle(initialEntry.title);
      setDescription(initialEntry.details);
      setStartTime(toLocalISOString(initialEntry.start));
      setEndTime(toLocalISOString(initialEntry.end));
      setSelectedAgent(initialEntry.agent || '');
      setPriority(initialEntry.priority);
      // Try to find graph ID from metadata if available (not in AgendaEntry yet, but we can improve)
    } else if (initialDate) {
      setTitle('');
      setDescription('');
      const start = new Date(initialDate);
      start.setHours(9, 0, 0, 0);
      const end = new Date(start);
      end.setHours(10, 30, 0, 0);
      setStartTime(toLocalISOString(start));
      setEndTime(toLocalISOString(end));
      setSelectedAgent('');
      setPriority('medium');
      setSelectedGraphId(null);
    }
  }, [initialEntry, initialDate, isOpen]);

  function toLocalISOString(date: Date) {
    const tzOffset = date.getTimezoneOffset() * 60000;
    const localISOTime = new Date(date.getTime() - tzOffset).toISOString().slice(0, 16);
    return localISOTime;
  }

  const handleSave = async () => {
    if (!title.trim() || !startTime || !endTime) {
      showToast('Please fill in all required fields.', 'error');
      return;
    }

    setExecuting(true);
    try {
      const url = isEdit 
        ? `${API_BASE}/agenda/events/${initialEntry.sourceId}`
        : `${API_BASE}/agenda/events`;
      
      const method = isEdit ? 'PATCH' : 'POST';
      
      const payload = {
        title,
        description,
        start: new Date(startTime).toISOString(),
        end: new Date(endTime).toISOString(),
        agent_id: selectedAgent || null,
        priority,
        workflow_id: selectedGraphId || undefined,
      };

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        showToast(isEdit ? 'Event updated.' : 'Event scheduled.', 'success');
        onSuccess();
        onClose();
      } else {
        const errData = await response.json();
        showToast(errData.detail || 'Failed to save event.', 'error');
      }
    } catch (error) {
      showToast('Error connecting to Command Center.', 'error');
    } finally {
      setExecuting(false);
    }
  };

  const handleCancelEvent = async () => {
    if (!initialEntry) return;
    
    if (!confirm('Are you sure you want to cancel this scheduled directive?')) return;

    setExecuting(true);
    try {
      const response = await fetch(`${API_BASE}/agenda/events/${initialEntry.sourceId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        showToast('Event cancelled.', 'success');
        onSuccess();
        onClose();
      } else {
        showToast('Failed to cancel event.', 'error');
      }
    } catch (error) {
      showToast('Error connecting to Command Center.', 'error');
    } finally {
      setExecuting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-[#0a0a0a]/80 backdrop-blur-xl"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="relative w-full max-w-xl bg-[#141414] border border-white/10 rounded-[32px] shadow-[0_32px_128px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-gradient-to-r from-[#1a1a1a] to-[#141414]">
              <div>
                <h2 className="text-2xl font-headline font-bold text-[#f4efee] tracking-tight">
                  {isEdit ? 'Refine Directive' : 'Schedule Directive'}
                </h2>
                <p className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] mt-1">
                  Temporal Strategic Planning
                </p>
              </div>
              <button 
                onClick={onClose}
                className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-all active:scale-90"
              >
                <span className="material-symbols-outlined text-[#8f8582]">close</span>
              </button>
            </div>

            {/* Form */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar">
              <div className="space-y-2">
                <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="The objective of this directive..."
                  className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] placeholder:text-[#5c5452] focus:outline-none focus:border-[#6e373c] transition-all"
                />
              </div>

              <div className="space-y-2">
                <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Context & Payload</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Detailed instructions for the assigned agent..."
                  rows={4}
                  className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] placeholder:text-[#5c5452] focus:outline-none focus:border-[#6e373c] transition-all resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Start Execution</label>
                  <input
                    type="datetime-local"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] focus:outline-none focus:border-[#6e373c] transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Target Completion</label>
                  <input
                    type="datetime-local"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] focus:outline-none focus:border-[#6e373c] transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Primary Agent</label>
                  <select
                    value={selectedAgent}
                    onChange={(e) => setSelectedAgent(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] focus:outline-none focus:border-[#6e373c] transition-all appearance-none cursor-pointer"
                  >
                    <option value="">Auto-Assign</option>
                    {agents.map(agent => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] focus:outline-none focus:border-[#6e373c] transition-all appearance-none cursor-pointer"
                  >
                    <option value="low">Low Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="high">High Priority</option>
                    <option value="critical">Critical Priority</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] ml-1">Workflow Template (Optional)</label>
                <select
                  value={selectedGraphId || ''}
                  onChange={(e) => setSelectedGraphId(e.target.value || null)}
                  className="w-full bg-[#1a1a1a] border border-white/5 rounded-2xl px-5 py-4 font-body text-sm text-[#f4efee] focus:outline-none focus:border-[#6e373c] transition-all appearance-none cursor-pointer"
                >
                  <option value="">None (Ad-hoc Task)</option>
                  {graphs.map(graph => (
                    <option key={graph.id} value={graph.id}>
                      {graph.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Footer */}
            <div className="p-8 border-t border-white/5 bg-[#101010]/95 flex items-center justify-between gap-4">
              {isEdit && (
                <button
                  onClick={handleCancelEvent}
                  disabled={executing}
                  className="px-6 py-4 rounded-2xl font-label text-[10px] uppercase tracking-[0.24em] text-[#ff7f88] border border-[#ff7f88]/20 hover:bg-[#ff7f88]/10 transition-all active:scale-95 disabled:opacity-50"
                >
                  Cancel Directive
                </button>
              )}
              
              <div className="flex-1 flex justify-end gap-4">
                <button
                  onClick={onClose}
                  className="px-6 py-4 rounded-2xl font-label text-[10px] uppercase tracking-[0.24em] text-[#8f8582] hover:text-white transition-all"
                >
                  Discard
                </button>
                <button
                  onClick={handleSave}
                  disabled={executing}
                  className="px-8 py-4 rounded-2xl bg-[#6e373c] hover:bg-[#8e474c] text-white font-label text-[10px] uppercase tracking-[0.24em] font-bold shadow-[0_8px_32px_rgba(110,55,60,0.3)] transition-all active:scale-95 disabled:opacity-50 flex items-center gap-2"
                >
                  {executing ? (
                    <span className="material-symbols-outlined animate-spin text-[18px]">refresh</span>
                  ) : (
                    <span className="material-symbols-outlined text-[18px]">verified</span>
                  )}
                  {isEdit ? 'Commit Changes' : 'Schedule Mission'}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
