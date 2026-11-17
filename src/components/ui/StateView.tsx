import React from 'react';
import { AlertCircle, CheckCircle2, Inbox, Loader2, Users } from 'lucide-react';
import { Button } from './Button';

type StateKind = 'loading' | 'empty' | 'error' | 'success' | 'no_users';

interface StateViewProps {
  kind: StateKind;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const StateView: React.FC<StateViewProps> = ({
  kind,
  title,
  description,
  actionLabel,
  onAction,
}) => {
  const iconMap: Record<StateKind, React.ReactNode> = {
    loading: <Loader2 className="h-6 w-6 text-[#7667F7] animate-spin" />,
    empty: <Inbox className="h-6 w-6 text-[#9299AC]" />,
    error: <AlertCircle className="h-6 w-6 text-[#F16C79]" />,
    success: <CheckCircle2 className="h-6 w-6 text-[#30C48D]" />,
    no_users: <Users className="h-6 w-6 text-[#36B9E9]" />,
  };

  return (
    <div className="rounded-2xl bg-[#171B29] border border-white/[0.07] p-8 text-center flex flex-col items-center justify-center max-w-md mx-auto">
      <div className="h-12 w-12 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mb-4">
        {iconMap[kind]}
      </div>
      <h3 className="text-base font-semibold text-[#F5F6FA]">{title}</h3>
      <p className="text-sm text-[#9299AC] mt-2 leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button onClick={onAction} variant="outline" size="sm" className="mt-5">
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
