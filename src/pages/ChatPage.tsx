import React, { useEffect, useRef, useState } from 'react';
import {
  Ban,
  Flag,
  Mic,
  PhoneOff,
  Send,
  SkipForward,
  UserPlus,
  Video,
} from 'lucide-react';
import { ChatMessage, UserProfile } from '../types/domain';
import { Avatar } from '../components/ui/Avatar';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';

interface ChatPageProps {
  peer: UserProfile;
  topic: string;
  initialMessages: ChatMessage[];
  isConnected: boolean;
  isConnectionPending: boolean;
  isTyping?: boolean;
  onSendMessage: (peerId: string, content: string) => void;
  onRequestConnection: (peer: UserProfile) => void;
  onBlockUser: (peer: UserProfile) => void;
  onReportUser: (peer: UserProfile, reason: string, details: string) => void;
  onViewPeerProfile: (peer: UserProfile) => void;
  onSkipToLobby: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({
  peer,
  topic,
  initialMessages,
  isConnected,
  isConnectionPending,
  isTyping = false,
  onSendMessage,
  onRequestConnection,
  onBlockUser,
  onReportUser,
  onViewPeerProfile,
  onSkipToLobby,
}) => {
  const [draft, setDraft] = useState('');
  const [ended, setEnded] = useState(false);

  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState('Inappropriate behavior');
  const [reportDetails, setReportDetails] = useState('');
  const [reportSubmitted, setReportSubmitted] = useState(false);
  const [blockOpen, setBlockOpen] = useState(false);

  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEnded(false);
    setReportSubmitted(false);
  }, [peer.id]);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [initialMessages.length, isTyping]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || ended) return;
    onSendMessage(peer.id, draft.trim());
    setDraft('');
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7.5rem)] lg:h-[calc(100vh-4rem)] rounded-2xl bg-[#111522] border border-white/[0.08] overflow-hidden">
      {/* Conversation Header */}
      <div className="px-4 sm:px-6 py-3.5 border-b border-white/[0.07] bg-[#171B29]/75 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => onViewPeerProfile(peer)}
          className="flex items-center gap-3 cursor-pointer group text-left min-w-0"
        >
          <Avatar
            name={peer.displayName}
            src={peer.avatarUrl}
            size="md"
            online={!ended}
          />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-sm font-semibold group-hover:text-[#36B9E9] transition truncate">
                {peer.displayName}
              </h2>
              <span className="text-xs text-[#9299AC] whitespace-nowrap">
                · {peer.category}
              </span>
            </div>
            <p className="text-xs text-[#9299AC] truncate">
              {ended ? 'Conversation ended' : topic}
            </p>
          </div>
        </button>

        {/* Actions + Non-MVP Audio/Video Future Preview */}
        <div className="flex flex-wrap items-center gap-2">
          <div
            title="Text chat only in MVP. Audio and video calls are planned for a future release."
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-[11px] text-[#9299AC] select-none"
          >
            <Mic className="h-3.5 w-3.5 opacity-45" />
            <Video className="h-3.5 w-3.5 opacity-45" />
            <span>A/V Future</span>
          </div>

          {!isConnected && (
            <Button
              size="sm"
              variant={isConnectionPending ? 'secondary' : 'outline'}
              disabled={isConnectionPending}
              onClick={() => onRequestConnection(peer)}
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span>
                {isConnectionPending ? 'Request Pending' : 'Request Connection'}
              </span>
            </Button>
          )}

          <Button size="sm" variant="ghost" onClick={onSkipToLobby}>
            <SkipForward className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Skip &amp; Find Another</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            aria-label="Report user"
            onClick={() => setReportOpen(true)}
          >
            <Flag className="h-3.5 w-3.5 text-[#F16C79]" />
            <span className="hidden xl:inline text-[#F16C79]">Report</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            aria-label="Block user"
            onClick={() => setBlockOpen(true)}
          >
            <Ban className="h-3.5 w-3.5 text-[#F16C79]" />
            <span className="hidden xl:inline text-[#F16C79]">Block</span>
          </Button>

          {!ended && (
            <Button size="sm" variant="danger" onClick={() => setEnded(true)}>
              <PhoneOff className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">End Conversation</span>
            </Button>
          )}
        </div>
      </div>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        <div className="text-center my-1">
          <span className="text-xs text-[#9299AC]">
            Text conversation started · Respectful dialogue guidelines apply
          </span>
        </div>

        {initialMessages.map((msg) => {
          const isSelf = msg.senderId === 'usr_self';
          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isSelf ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[82%] sm:max-w-[68%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                  isSelf
                    ? 'bg-[#7667F7] text-[#F5F6FA] rounded-br-sm'
                    : 'bg-[#171B29] border border-white/[0.07] text-[#F5F6FA] rounded-bl-sm'
                }`}
              >
                {msg.content}
              </div>
              <span className="font-mono text-[11px] text-[#9299AC] mt-1 px-1 tabular-nums">
                {msg.createdAt}
              </span>
            </div>
          );
        })}

        {isTyping && !ended && (
          <div className="text-xs text-[#9299AC] italic px-1">
            {peer.displayName} is typing...
          </div>
        )}

        {reportSubmitted && (
          <div className="p-3.5 rounded-xl bg-[#30C48D]/10 border border-[#30C48D]/30 text-xs text-[#30C48D] text-center max-w-md mx-auto">
            Report submitted to our moderation team. Thank you for helping keep
            Studable safe.
          </div>
        )}

        {ended && (
          <div className="p-6 rounded-2xl bg-[#171B29] border border-white/[0.08] text-center space-y-3 max-w-md mx-auto my-6">
            <h3 className="text-base font-semibold">Conversation Ended</h3>
            <p className="text-xs text-[#9299AC] leading-relaxed">
              You can request a connection if you&apos;d like to stay in touch, or
              head back to discover someone new.
            </p>
            <div className="flex flex-wrap justify-center gap-2.5 pt-1">
              <Button size="sm" onClick={onSkipToLobby}>
                Find Another Match
              </Button>
              {!isConnected && !isConnectionPending && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onRequestConnection(peer)}
                >
                  Request Connection
                </Button>
              )}
            </div>
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      {/* Composer */}
      <form
        onSubmit={handleSend}
        className="p-3 sm:p-4 border-t border-white/[0.07] bg-[#171B29]/50 flex items-center gap-2.5"
      >
        <input
          value={draft}
          disabled={ended}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={
            ended
              ? 'This conversation has ended'
              : 'Write a thoughtful message...'
          }
          aria-label="Message input"
          className="flex-1 h-11 px-4 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7] disabled:opacity-50"
        />
        <Button type="submit" disabled={ended || !draft.trim()} className="h-11">
          <Send className="h-4 w-4" />
          <span className="hidden sm:inline">Send</span>
        </Button>
      </form>

      {/* Report Modal */}
      <Modal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title={`Report ${peer.displayName}`}
        description="Reports are reviewed confidentially by our moderation team."
      >
        <div className="space-y-4">
          <div>
            <label
              htmlFor="report-reason"
              className="block text-xs font-medium text-[#9299AC] mb-1.5"
            >
              Reason
            </label>
            <select
              id="report-reason"
              value={reportReason}
              onChange={(e) => setReportReason(e.target.value)}
              className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            >
              <option>Inappropriate behavior</option>
              <option>Spam or unsolicited promotion</option>
              <option>Harassment or disrespectful conduct</option>
              <option>Impersonation</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="report-details"
              className="block text-xs font-medium text-[#9299AC] mb-1.5"
            >
              Additional Context (Optional)
            </label>
            <textarea
              id="report-details"
              rows={3}
              value={reportDetails}
              onChange={(e) => setReportDetails(e.target.value)}
              placeholder="Briefly describe what happened..."
              className="w-full p-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] resize-none"
            />
          </div>
          <div className="flex justify-end gap-2.5">
            <Button variant="ghost" onClick={() => setReportOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                onReportUser(peer, reportReason, reportDetails);
                setReportSubmitted(true);
                setReportOpen(false);
                setEnded(true);
              }}
            >
              Submit Report
            </Button>
          </div>
        </div>
      </Modal>

      {/* Block Modal */}
      <Modal
        open={blockOpen}
        onClose={() => setBlockOpen(false)}
        title={`Block ${peer.displayName}?`}
        description="They will no longer be able to match with or message you."
      >
        <div className="flex justify-end gap-2.5 pt-2">
          <Button variant="ghost" onClick={() => setBlockOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              setBlockOpen(false);
              setEnded(true);
              onBlockUser(peer);
            }}
          >
            Confirm Block
          </Button>
        </div>
      </Modal>
    </div>
  );
};
