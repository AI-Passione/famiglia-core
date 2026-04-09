import type { GraphDefinition } from '../../types';

interface OperationsHubProps {
  graphs: GraphDefinition[];
  onExecuteDirective: () => void;
}

export function OperationsHub({ }: OperationsHubProps) {
  return (
    <div className="flex flex-col gap-6">
      {/* Operations Hub is now primarily a trigger point for the Directive Modal and specialized operational views */}
    </div>
  );
}
