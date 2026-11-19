import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  interactive?: boolean;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  interactive = false,
  onClick,
}) => (
  <div
    onClick={onClick}
    className={`rounded-2xl bg-[#171B29] border border-white/[0.07] p-6 transition-colors duration-150 ${
      interactive
        ? 'cursor-pointer hover:border-[#7667F7]/40 hover:bg-[#1B2031]'
        : ''
    } ${className}`}
  >
    {children}
  </div>
);
