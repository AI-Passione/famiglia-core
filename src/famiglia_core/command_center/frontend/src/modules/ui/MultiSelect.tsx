import { useState, useRef, useEffect } from 'react';

interface Option {
  id: number;
  name: string;
}

interface MultiSelectProps {
  label: string;
  options: Option[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
}

export function MultiSelect({ label, options, selectedIds, onChange }: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleOption = (id: number) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((item) => item !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const selectedNames = options
    .filter((opt) => selectedIds.includes(opt.id))
    .map((opt) => opt.name)
    .join(', ');

  return (
    <div className="space-y-2 relative" ref={containerRef}>
      <label className="block text-xs font-headline uppercase tracking-widest text-on-surface-variant/70">
        {label}
      </label>
      <div
        className="w-full bg-surface-container-lowest border border-outline-variant/30 px-4 py-3 text-white cursor-pointer flex justify-between items-center group hover:border-tertiary/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="truncate text-sm">
          {selectedNames || <span className="text-on-surface-variant/40 italic text-xs">None selected</span>}
        </span>
        <svg
          className={`w-4 h-4 text-on-surface-variant transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {isOpen && (
        <div className="absolute z-[100] w-full mt-1 bg-[#1a1a1a] border border-outline-variant/30 max-h-60 overflow-y-auto shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-top-2 duration-200">
          {options.length === 0 ? (
            <div className="px-4 py-3 text-xs text-on-surface-variant/50 italic text-center">
              No options available
            </div>
          ) : (
            options.map((option) => (
              <div
                key={option.id}
                className={`px-4 py-2.5 text-sm cursor-pointer flex items-center justify-between transition-colors ${
                  selectedIds.includes(option.id)
                    ? 'bg-tertiary/10 text-tertiary shadow-[inset_2px_0_0_0_currentColor]'
                    : 'text-on-surface-variant hover:bg-surface-container-low hover:text-white'
                }`}
                onClick={() => toggleOption(option.id)}
              >
                <span>{option.name}</span>
                {selectedIds.includes(option.id) && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
