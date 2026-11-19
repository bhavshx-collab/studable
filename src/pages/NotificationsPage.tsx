import React from 'react';
import {
  Bell,
  CheckCheck,
  MessageSquare,
  ShieldAlert,
  UserPlus,
} from 'lucide-react';
import { AppNotification } from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StateView } from '../components/ui/StateView';

interface NotificationsPageProps {
  notifications: AppNotification[];
  onMarkAllRead: () => void;
  onOpenNotification?: (notif: AppNotification) => void;
}

export const NotificationsPage: React.FC<NotificationsPageProps> = ({
  notifications,
  onMarkAllRead,
  onOpenNotification,
}) => {
  const iconFor = (type: AppNotification['type']) => {
    if (type === 'connection_request' || type === 'connection_accepted')
      return <UserPlus className="h-4 w-4 text-[#7667F7]" />;
    if (type === 'new_message')
      return <MessageSquare className="h-4 w-4 text-[#36B9E9]" />;
    if (type === 'moderation')
      return <ShieldAlert className="h-4 w-4 text-[#30C48D]" />;
    return <Bell className="h-4 w-4 text-[#9299AC]" />;
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.07]">
        <div>
          <h1 className="font-display text-2xl font-semibold">Notifications</h1>
          <p className="text-sm text-[#9299AC] mt-1">
            Connection requests, accepted connections, messages, and safety
            updates.
          </p>
        </div>
        {notifications.some((n) => !n.read) && (
          <Button variant="outline" size="sm" onClick={onMarkAllRead}>
            <CheckCheck className="h-4 w-4" /> Mark all read
          </Button>
        )}
      </div>

      {notifications.length === 0 ? (
        <StateView
          kind="empty"
          title="All caught up"
          description="You have no notifications right now."
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <Card
              key={n.id}
              interactive={Boolean(n.relatedUserId)}
              onClick={() => n.relatedUserId && onOpenNotification?.(n)}
              className={`flex items-start justify-between gap-4 p-5 ${
                !n.read ? 'border-[#7667F7]/40 bg-[#1A1F33]' : ''
              }`}
            >
              <div className="flex items-start gap-3.5">
                <div className="h-9 w-9 rounded-xl bg-white/[0.05] flex items-center justify-center shrink-0">
                  {iconFor(n.type)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-medium text-[#F5F6FA]">
                      {n.title}
                    </h3>
                    {!n.read && (
                      <span className="text-[11px] font-medium text-[#36B9E9]">
                        · Unread
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#9299AC] mt-1 leading-relaxed">
                    {n.description}
                  </p>
                </div>
              </div>
              <span className="font-mono text-[11px] text-[#9299AC] shrink-0 tabular-nums">
                {n.timestamp}
              </span>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
