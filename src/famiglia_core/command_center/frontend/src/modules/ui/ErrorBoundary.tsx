import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-10 text-center bg-[#131313] border border-[#ffb3b5]/20 rounded-[32px] m-4">
          <span className="material-symbols-outlined text-6xl text-primary mb-4 animate-pulse">warning</span>
          <h1 className="font-headline italic text-2xl text-primary mb-2">Terminal Critical Failure</h1>
          <p className="font-body text-outline text-sm mb-6 max-w-md">
            The encrypted connection has encountered a protocol error. Access to this sector is temporarily suspended.
          </p>
          <div className="bg-black/40 p-4 rounded-xl border border-outline/10 w-full max-w-lg mb-8 text-left overflow-auto max-h-40 custom-scrollbar">
            <code className="text-[10px] text-primary/70 font-mono leading-relaxed">
              {this.state.error?.toString()}
              {this.state.error?.stack && (
                <div className="mt-2 text-outline/50">{this.state.error.stack.split('\n').slice(0, 3).join('\n')}</div>
              )}
            </code>
          </div>
          <button
            onClick={() => {
              localStorage.clear();
              window.location.reload();
            }}
            className="px-8 py-3 bg-[#4A0404] text-white rounded-xl font-label text-[10px] uppercase tracking-[0.2em] hover:bg-[#630606] transition-all border border-[#ffb3b5]/20 shadow-lg shadow-black"
          >
            Clear Local Intelligence & Reboot
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
