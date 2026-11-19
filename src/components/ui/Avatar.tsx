import React, { useState } from 'react';

interface AvatarProps {
  name: string;
  src?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  online?: boolean;
}

export const Avatar: React.FC<AvatarProps> = ({
  name,
  src,
  size = 'md',
  online,
}) => {
  const [imgFailed, setImgFailed] = useState(false);

  const initials = name
    .split(' ')
    .filter(Boolean)
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const sizes = {
    sm: 'h-9 w-9 text-xs',
    md: 'h-11 w-11 text-sm',
    lg: 'h-14 w-14 text-base',
    xl: 'h-20 w-20 text-xl',
  };

  return (
    <div className="relative inline-flex shrink-0">
      {src && !imgFailed ? (
        <img
          src={src}
          alt={name}
          referrerPolicy="no-referrer"
          onError={() => setImgFailed(true)}
          className={`${sizes[size]} rounded-full object-cover border border-white/15 bg-[#111522]`}
        />
      ) : (
        <div
          className={`${sizes[size]} rounded-full bg-gradient-to-br from-[#7667F7]/30 to-[#36B9E9]/25 border border-white/15 flex items-center justify-center font-semibold text-[#F5F6FA]`}
        >
          {initials}
        </div>
      )}
      {online !== undefined && (
        <span
          aria-label={online ? 'Active' : 'Offline'}
          className={`absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full ring-2 ring-[#171B29] ${
            online ? 'bg-[#30C48D]' : 'bg-[#9299AC]/50'
          }`}
        />
      )}
    </div>
  );
};
