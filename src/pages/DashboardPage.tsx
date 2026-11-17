import React from 'react';
import {
  ArrowUpRight,
  Briefcase,
  CalendarClock,
  Compass,
  Sparkles,
  UserPlus,
} from 'lucide-react';
import { ConnectionRecord, UserProfile } from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Avatar } from '../components/ui/Avatar';
import { POPULAR_TOPICS } from '../data/prototypeMocks';

interface DashboardPageProps {
  currentUser: UserProfile;
  liveOnlineCount: number | null;
  suggestedPeers: UserProfile[];
  recentConnections: ConnectionRecord[];
  onStartRandomConnect: () => void;
  onExploreInterests: (topic?: string) => void;
  onFindProfessionals: () => void;
  onViewProfile: (user: UserProfile) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  currentUser,
  liveOnlineCount,
  suggestedPeers,
  recentConnections,
  onStartRandomConnect,
  onExploreInterests,
  onFindProfessionals,
  onViewProfile,
}) => {
  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-white/[0.07]">
        <div>
          <p className="text-xs font-medium text-[#36B9E9] mb-1">
            Find someone worth talking to
          </p>
          <h1 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight">
            Welcome back, {currentUser.displayName}
          </h1>
          <p className="text-sm text-[#9299AC] mt-1">
            There&apos;s someone new worth meeting today.
          </p>
        </div>

        <div className="text-xs text-[#9299AC] tabular-nums">
          {liveOnlineCount !== null
            ? `${liveOnlineCount} people online now`
            : 'Live online count activates with backend socket'}
        </div>
      </div>

      {/* 3 Primary Matching Cards */}
      <div className="grid md:grid-cols-3 gap-5">
        <Card className="flex flex-col justify-between bg-gradient-to-b from-[#181D2D] to-[#131726]">
          <div>
            <div className="h-10 w-10 rounded-xl bg-[#7667F7]/15 border border-[#7667F7]/30 flex items-center justify-center mb-4">
              <Sparkles className="h-5 w-5 text-[#7667F7]" />
            </div>
            <p className="text-xs font-medium text-[#9299AC]">Meet Someone New</p>
            <h2 className="text-lg font-semibold mt-1 mb-2">Spontaneous Match</h2>
            <p className="text-sm text-[#9299AC] leading-relaxed">
              Start a spontaneous conversation with someone available right now.
            </p>
          </div>
          <Button onClick={onStartRandomConnect} className="w-full mt-6">
            Random Connect
          </Button>
        </Card>

        <Card className="flex flex-col justify-between">
          <div>
            <div className="h-10 w-10 rounded-xl bg-[#36B9E9]/15 border border-[#36B9E9]/30 flex items-center justify-center mb-4">
              <Compass className="h-5 w-5 text-[#36B9E9]" />
            </div>
            <p className="text-xs font-medium text-[#9299AC]">
              Find People Like Me
            </p>
            <h2 className="text-lg font-semibold mt-1 mb-2">Interest Discovery</h2>
            <p className="text-sm text-[#9299AC] leading-relaxed">
              Discover people who share your interests, goals and passions.
            </p>
          </div>
          <Button
            variant="secondary"
            onClick={() => onExploreInterests()}
            className="w-full mt-6"
          >
            Explore Interests
          </Button>
        </Card>

        <Card className="flex flex-col justify-between">
          <div>
            <div className="h-10 w-10 rounded-xl bg-[#30C48D]/15 border border-[#30C48D]/30 flex items-center justify-center mb-4">
              <Briefcase className="h-5 w-5 text-[#30C48D]" />
            </div>
            <p className="text-xs font-medium text-[#9299AC]">
              Talk to a Professional
            </p>
            <h2 className="text-lg font-semibold mt-1 mb-2">
              Career &amp; Mentorship
            </h2>
            <p className="text-sm text-[#9299AC] leading-relaxed">
              Connect with experienced professionals and explore new perspectives.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={onFindProfessionals}
            className="w-full mt-6"
          >
            Find Professionals
          </Button>
        </Card>
      </div>

      {/* Popular Topics + Recent Connections */}
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Popular Conversation Topics</h3>
            <span className="text-xs text-[#9299AC]">Select to match</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {POPULAR_TOPICS.map((topic) => (
              <button
                key={topic}
                type="button"
                onClick={() => onExploreInterests(topic)}
                className="min-h-[38px] px-3.5 py-2 rounded-xl bg-[#111522] border border-white/[0.08] hover:border-[#36B9E9]/50 text-xs text-[#F5F6FA] transition flex items-center gap-1.5 cursor-pointer"
              >
                <span>{topic}</span>
                <ArrowUpRight className="h-3.5 w-3.5 text-[#9299AC]" />
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Recent Connections</h3>
            <span className="text-xs text-[#9299AC] tabular-nums">
              {recentConnections.length} total
            </span>
          </div>
          <div className="divide-y divide-white/[0.06]">
            {recentConnections.slice(0, 3).map((conn) => (
              <button
                key={conn.id}
                type="button"
                onClick={() => onViewProfile(conn.user)}
                className="w-full py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-3 text-left hover:opacity-90 transition cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Avatar
                    name={conn.user.displayName}
                    src={conn.user.avatarUrl}
                    size="sm"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">
                      {conn.user.displayName}
                    </p>
                    <p className="text-xs text-[#9299AC] truncate">
                      {conn.user.category} · {conn.user.headline}
                    </p>
                  </div>
                </div>
                <span
                  className={`text-xs font-medium shrink-0 ${
                    conn.status === 'accepted'
                      ? 'text-[#30C48D]'
                      : 'text-[#9299AC]'
                  }`}
                >
                  {conn.status === 'accepted' ? 'Connected' : 'Pending'}
                </span>
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* Tablet / Mobile Secondary Panel */}
      <div className="xl:hidden space-y-6 pt-2">
        <DashboardRightPanel
          suggestedPeers={suggestedPeers}
          onViewProfile={onViewProfile}
        />
      </div>
    </div>
  );
};

export const DashboardRightPanel: React.FC<{
  suggestedPeers: UserProfile[];
  onViewProfile: (user: UserProfile) => void;
}> = ({ suggestedPeers, onViewProfile }) => (
  <>
    <div>
      <h3 className="text-xs font-semibold text-[#9299AC] mb-3">
        Suggested Connections
      </h3>
      <div className="divide-y divide-white/[0.06] rounded-2xl bg-[#171B29] border border-white/[0.07] px-4">
        {suggestedPeers.map((peer) => (
          <div key={peer.id} className="py-3.5 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() => onViewProfile(peer)}
                className="flex items-center gap-2.5 cursor-pointer min-w-0 text-left"
              >
                <Avatar
                  name={peer.displayName}
                  src={peer.avatarUrl}
                  size="sm"
                />
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate text-[#F5F6FA]">
                    {peer.displayName}
                  </p>
                  <p className="text-xs text-[#9299AC] truncate">
                    {peer.category}
                  </p>
                </div>
              </button>
              <button
                type="button"
                onClick={() => onViewProfile(peer)}
                aria-label={`View ${peer.displayName}'s profile`}
                className="min-h-[36px] min-w-[36px] flex items-center justify-center rounded-lg bg-white/[0.04] hover:bg-[#7667F7]/20 text-[#9299AC] hover:text-[#F5F6FA] cursor-pointer"
              >
                <UserPlus className="h-3.5 w-3.5" />
              </button>
            </div>
            <p className="text-xs text-[#9299AC] line-clamp-2">{peer.headline}</p>
          </div>
        ))}
      </div>
    </div>

    <div className="p-4 rounded-2xl bg-[#171B29]/60 border border-dashed border-white/12">
      <div className="flex items-center justify-between mb-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#F5F6FA]">
          <CalendarClock className="h-4 w-4 text-[#7667F7]" />
          Upcoming Sessions
        </span>
        <span className="text-[11px] text-[#9299AC]">Future Feature</span>
      </div>
      <p className="text-xs text-[#9299AC] leading-relaxed">
        Scheduled mentor office hours and structured group topics will appear here
        in a future release.
      </p>
    </div>

    <div>
      <h3 className="text-xs font-semibold text-[#9299AC] mb-3">
        Recent Activity
      </h3>
      <ul className="space-y-2.5 text-xs text-[#9299AC]">
        <li className="p-3 rounded-xl bg-[#171B29] border border-white/[0.06]">
          Elena Vance accepted your connection request.
        </li>
        <li className="p-3 rounded-xl bg-[#171B29] border border-white/[0.06]">
          Interest matching updated with AI and Machine Learning.
        </li>
      </ul>
    </div>
  </>
);
