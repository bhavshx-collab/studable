import React, { useState } from 'react';
import { Check, MessageSquare, Trash2, X } from 'lucide-react';
import { ConnectionRecord, UserProfile } from '../types/domain';
import { Avatar } from '../components/ui/Avatar';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StateView } from '../components/ui/StateView';

interface ConnectionsPageProps {
  connections: ConnectionRecord[];
  onAccept: (id: string) => void;
  onRejectOrRemove: (id: string) => void;
  onOpenProfile: (user: UserProfile) => void;
  onOpenChat: (user: UserProfile) => void;
  onExploreMatches: () => void;
}

export const ConnectionsPage: React.FC<ConnectionsPageProps> = ({
  connections,
  onAccept,
  onRejectOrRemove,
  onOpenProfile,
  onOpenChat,
  onExploreMatches,
}) => {
  const [tab, setTab] = useState<'accepted' | 'pending'>('accepted');

  const accepted = connections.filter((c) => c.status === 'accepted');
  const pending = connections.filter((c) => c.status !== 'accepted');
  const list = tab === 'accepted' ? accepted : pending;

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-white/[0.07]">
        <div>
          <h1 className="font-display text-2xl font-semibold">My Connections</h1>
          <p className="text-sm text-[#9299AC] mt-1">
            People you&apos;ve mutually connected with after meaningful
            conversations.
          </p>
        </div>

        <div className="inline-flex p-1 rounded-xl bg-[#111522] border border-white/[0.08]">
          <button
            type="button"
            onClick={() => setTab('accepted')}
            className={`min-h-[38px] px-4 py-1.5 rounded-lg text-xs font-medium tabular-nums cursor-pointer transition ${
              tab === 'accepted'
                ? 'bg-[#7667F7] text-[#F5F6FA]'
                : 'text-[#9299AC] hover:text-[#F5F6FA]'
            }`}
          >
            Accepted ({accepted.length})
          </button>
          <button
            type="button"
            onClick={() => setTab('pending')}
            className={`min-h-[38px] px-4 py-1.5 rounded-lg text-xs font-medium tabular-nums cursor-pointer transition ${
              tab === 'pending'
                ? 'bg-[#7667F7] text-[#F5F6FA]'
                : 'text-[#9299AC] hover:text-[#F5F6FA]'
            }`}
          >
            Pending ({pending.length})
          </button>
        </div>
      </div>

      {list.length === 0 ? (
        <StateView
          kind="empty"
          title={
            tab === 'accepted' ? 'No connections yet' : 'No pending requests'
          }
          description="Great conversations often lead to lasting connections. Visit the Connection Lobby to meet someone new."
          actionLabel="Go to Connect Lobby"
          onAction={onExploreMatches}
        />
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {list.map((conn) => (
            <Card key={conn.id} className="flex flex-col justify-between gap-4">
              <button
                type="button"
                onClick={() => onOpenProfile(conn.user)}
                className="flex items-start gap-3.5 cursor-pointer text-left"
              >
                <Avatar
                  name={conn.user.displayName}
                  src={conn.user.avatarUrl}
                  size="md"
                />
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold truncate text-[#F5F6FA]">
                    {conn.user.displayName}
                  </h3>
                  <p className="text-xs text-[#9299AC] truncate mt-0.5">
                    {conn.user.category} · {conn.user.headline}
                  </p>
                  {conn.sharedTopic && (
                    <p className="text-xs text-[#36B9E9] mt-1.5">
                      Met via {conn.sharedTopic}
                    </p>
                  )}
                </div>
              </button>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.06]">
                {conn.status === 'accepted' && (
                  <>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onRejectOrRemove(conn.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-[#F16C79]" /> Remove
                    </Button>
                    <Button size="sm" onClick={() => onOpenChat(conn.user)}>
                      <MessageSquare className="h-3.5 w-3.5" /> Message
                    </Button>
                  </>
                )}
                {conn.status === 'pending_incoming' && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onRejectOrRemove(conn.id)}
                    >
                      <X className="h-3.5 w-3.5" /> Reject
                    </Button>
                    <Button size="sm" onClick={() => onAccept(conn.id)}>
                      <Check className="h-3.5 w-3.5" /> Accept
                    </Button>
                  </>
                )}
                {conn.status === 'pending_outgoing' && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onRejectOrRemove(conn.id)}
                  >
                    Cancel Request
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
