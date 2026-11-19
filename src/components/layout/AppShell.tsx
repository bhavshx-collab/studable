import React, { useState } from 'react';
import {
  Bell,
  Compass,
  Home,
  Menu,
  MessageSquare,
  Settings,
  Sparkles,
  User,
  Users,
  X,
} from 'lucide-react';
import { UserProfile } from '../../types/domain';
import { Avatar } from '../ui/Avatar';

export type AppRoute =
  | 'dashboard'
  | 'discover'
  | 'connect'
  | 'connections'
  | 'messages'
  | 'notifications'
  | 'profile'
  | 'settings';

interface AppShellProps {
  activeRoute: AppRoute;
  onNavigate: (route: AppRoute) => void;
  currentUser: UserProfile;
  unreadNotifications: number;
  rightPanel?: React.ReactNode;
  children: React.ReactNode;
}

const navItems: { id: AppRoute; label: string; icon: React.ReactNode }[] = [
  { id: 'dashboard', label: 'Home', icon: <Home className="h-4 w-4" /> },
  { id: 'discover', label: 'Discover', icon: <Compass className="h-4 w-4" /> },
  { id: 'connect', label: 'Connect', icon: <Sparkles className="h-4 w-4" /> },
  { id: 'connections', label: 'My Connections', icon: <Users className="h-4 w-4" /> },
  { id: 'messages', label: 'Messages', icon: <MessageSquare className="h-4 w-4" /> },
  { id: 'notifications', label: 'Notifications', icon: <Bell className="h-4 w-4" /> },
  { id: 'profile', label: 'Profile', icon: <User className="h-4 w-4" /> },
  { id: 'settings', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
];

export const AppShell: React.FC<AppShellProps> = ({
  activeRoute,
  onNavigate,
  currentUser,
  unreadNotifications,
  rightPanel,
  children,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  const renderNavList = (onItemClick?: () => void) => (
    <nav className="space-y-1" aria-label="Main navigation">
      {navItems.map((item) => {
        const active = activeRoute === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              onNavigate(item.id);
              onItemClick?.();
            }}
            className={`w-full min-h-[42px] flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7667F7] ${
              active
                ? 'bg-[#7667F7]/15 text-[#F5F6FA] border border-[#7667F7]/30'
                : 'text-[#9299AC] hover:text-[#F5F6FA] hover:bg-white/[0.04] border border-transparent'
            }`}
          >
            <span className="flex items-center gap-3">
              <span className={active ? 'text-[#7667F7]' : ''}>{item.icon}</span>
              <span>{item.label}</span>
            </span>
            {item.id === 'notifications' && unreadNotifications > 0 && (
              <span className="font-mono text-xs text-[#36B9E9] tabular-nums">
                {unreadNotifications}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-[#0B0D14] text-[#F5F6FA] flex flex-col lg:flex-row">
      {/* Compact Mobile Header (<= 15% mobile viewport height) */}
      <header className="lg:hidden sticky top-0 z-30 glass-surface border-b border-white/[0.07] px-4 h-14 flex items-center justify-between">
        <button
          type="button"
          onClick={() => onNavigate('dashboard')}
          className="font-display font-semibold text-base tracking-tight text-[#F5F6FA] whitespace-nowrap"
        >
          Studable
        </button>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onNavigate('connect')}
            className="min-h-[38px] px-3.5 rounded-lg bg-[#7667F7] hover:bg-[#6656EB] text-xs font-medium text-[#F5F6FA] whitespace-nowrap transition-colors"
          >
            Connect Now
          </button>
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation menu"
            className="min-h-[40px] min-w-[40px] flex items-center justify-center rounded-lg hover:bg-white/5 text-[#9299AC] hover:text-[#F5F6FA]"
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* Mobile Navigation Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/70"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative w-72 max-w-[85vw] bg-[#111522] border-r border-white/10 p-5 flex flex-col justify-between z-10">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="font-display font-semibold text-base tracking-tight">
                  Studable
                </span>
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  aria-label="Close navigation menu"
                  className="min-h-[40px] min-w-[40px] flex items-center justify-center rounded-lg text-[#9299AC] hover:text-[#F5F6FA]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              {renderNavList(() => setMobileOpen(false))}
            </div>

            <button
              type="button"
              onClick={() => {
                onNavigate('profile');
                setMobileOpen(false);
              }}
              className="pt-4 border-t border-white/[0.07] flex items-center gap-3 text-left"
            >
              <Avatar
                name={currentUser.displayName}
                src={currentUser.avatarUrl}
                size="sm"
              />
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {currentUser.displayName}
                </p>
                <p className="text-xs text-[#9299AC] truncate">
                  {currentUser.category}
                </p>
              </div>
            </button>
          </aside>
        </div>
      )}

      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:fixed lg:inset-y-0 bg-[#111522] border-r border-white/[0.07] p-5 justify-between">
        <div>
          <div className="px-2 mb-8">
            <button
              type="button"
              onClick={() => onNavigate('dashboard')}
              className="font-display font-bold text-lg tracking-tight text-[#F5F6FA] whitespace-nowrap cursor-pointer"
            >
              Studable
            </button>
          </div>
          {renderNavList()}
        </div>

        <button
          type="button"
          onClick={() => onNavigate('profile')}
          className="flex items-center gap-3 p-3 rounded-xl bg-[#171B29] border border-white/[0.06] hover:border-white/15 transition text-left cursor-pointer"
        >
          <Avatar
            name={currentUser.displayName}
            src={currentUser.avatarUrl}
            size="sm"
          />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-[#F5F6FA] truncate">
              {currentUser.displayName}
            </p>
            <p className="text-xs text-[#9299AC] truncate">{currentUser.category}</p>
          </div>
        </button>
      </aside>

      {/* Main Content Area + Optional Right Rail */}
      <div className="flex-1 lg:pl-64 flex flex-col xl:flex-row min-h-screen">
        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 lg:py-8 max-w-5xl w-full mx-auto">
          {children}
        </main>
        {rightPanel && (
          <aside className="hidden xl:block w-80 shrink-0 border-l border-white/[0.07] bg-[#111522]/40 p-6 space-y-6">
            {rightPanel}
          </aside>
        )}
      </div>
    </div>
  );
};
