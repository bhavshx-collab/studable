import React from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: React.ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-[#7667F7] hover:bg-[#6656EB] text-[#F5F6FA] border border-[#7667F7]',
  secondary:
    'bg-[#36B9E9]/15 hover:bg-[#36B9E9]/25 text-[#36B9E9] border border-[#36B9E9]/35',
  outline:
    'bg-[#171B29] hover:bg-[#1E2436] text-[#F5F6FA] border border-white/12',
  ghost:
    'bg-transparent hover:bg-white/[0.06] text-[#9299AC] hover:text-[#F5F6FA] border border-transparent',
  danger:
    'bg-[#F16C79]/15 hover:bg-[#F16C79]/25 text-[#F16C79] border border-[#F16C79]/35',
};

const sizeClasses: Record<Size, string> = {
  sm: 'min-h-[40px] px-4 py-2 text-xs rounded-lg gap-1.5',
  md: 'min-h-[42px] px-5 py-2.5 text-sm rounded-xl gap-2',
  lg: 'min-h-[48px] px-6 py-3 text-sm rounded-xl gap-2.5',
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  leftIcon,
  children,
  className = '',
  disabled,
  ...props
}) => (
  <button
    disabled={disabled || loading}
    className={`inline-flex items-center justify-center font-medium whitespace-nowrap shrink-0 transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7667F7] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0B0D14] disabled:opacity-50 disabled:pointer-events-none active:scale-[0.99] cursor-pointer ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    {...props}
  >
    {loading ? (
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
    ) : (
      leftIcon
    )}
    <span>{children}</span>
  </button>
);
