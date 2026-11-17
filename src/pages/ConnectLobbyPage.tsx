import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Clock,
  Globe,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from 'lucide-react';
import {
  AudiencePreference,
  InterestTag,
  MatchLifecycleState,
  MatchProposal,
  UserProfile,
} from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Avatar } from '../components/ui/Avatar';
import { StateView } from '../components/ui/StateView';

const INTEREST_OPTIONS: InterestTag[] = [
  'Technology',
  'AI and Machine Learning',
  'Programming',
  'Startups',
  'Business',
  'Career Development',
  'Design',
  'Education',
  'Personal Growth',
  'Entrepreneurship',
  'Other',
];

interface ConnectLobbyPageProps {
  defaultAudience?: AudiencePreference;
  defaultTopic?: string;
  liveOnlineCount: number | null;
  prototypePeers: UserProfile[];
  onEnterChat: (peer: UserProfile, topic: string) => void;
}

export const ConnectLobbyPage: React.FC<ConnectLobbyPageProps> = ({
  defaultAudience = 'Anyone',
  defaultTopic = 'Building reliable real-world AI products',
  liveOnlineCount,
  prototypePeers,
  onEnterChat,
}) => {
  const [randomAudience, setRandomAudience] =
    useState<AudiencePreference>(defaultAudience);
  const [interestAudience, setInterestAudience] =
    useState<AudiencePreference>(defaultAudience);
  const [selectedInterests, setSelectedInterests] = useState<InterestTag[]>([
    'Technology',
    'AI and Machine Learning',
  ]);
  const [topic, setTopic] = useState(defaultTopic);
  const [language, setLanguage] = useState('English');

  const [matchState, setMatchState] = useState<MatchLifecycleState>('idle');
  const [activeTopic, setActiveTopic] = useState('');
  const [proposal, setProposal] = useState<MatchProposal | null>(null);

  useEffect(() => {
    setRandomAudience(defaultAudience);
    setInterestAudience(defaultAudience);
  }, [defaultAudience]);

  useEffect(() => {
    if (defaultTopic) setTopic(defaultTopic);
  }, [defaultTopic]);

  const toggleInterest = (tag: InterestTag) => {
    setSelectedInterests((prev) =>
      prev.includes(tag) ? prev.filter((i) => i !== tag) : [...prev, tag]
    );
  };

  const startMatching = (mode: 'random' | 'interest') => {
    const chosenTopic =
      mode === 'random'
        ? `Spontaneous Conversation · ${randomAudience}`
        : topic.trim() || selectedInterests.join(', ') || 'General Discussion';

    const matchedPeer =
      mode === 'random' && randomAudience === 'Professionals'
        ? prototypePeers[0]
        : prototypePeers[1] ?? prototypePeers[0];

    setActiveTopic(chosenTopic);
    setMatchState('queuing');
    setProposal({
      matchId: `match_proto_${Date.now()}`,
      peer: matchedPeer,
      topic: chosenTopic,
      mode,
      expiresAtIso: new Date(Date.now() + 30000).toISOString(),
      selfAccepted: false,
      peerAccepted: false,
    });
  };

  const handleAcceptMatch = () => {
    if (!proposal) return;
    setProposal({ ...proposal, selfAccepted: true });
    setMatchState('awaiting_peer_acceptance');
  };

  const handleDeclineMatch = () => {
    setProposal(null);
    setMatchState('idle');
  };

  // Active Matching Experience
  if (matchState !== 'idle') {
    return (
      <div className="max-w-xl mx-auto py-6 space-y-6">
        {/* Prototype State Switcher for inspecting all matching lifecycle states */}
        <div className="p-3.5 rounded-xl bg-[#111522] border border-white/[0.08] flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-[#9299AC] font-medium">Prototype Flow:</span>
          <div className="flex flex-wrap gap-1.5">
            {(
              [
                ['queuing', 'Searching'],
                ['match_found', 'Match Found'],
                ['awaiting_peer_acceptance', 'Mutual Wait'],
                ['no_match', 'No Match'],
                ['timeout', 'Timeout'],
                ['error', 'Error'],
              ] as [MatchLifecycleState, string][]
            ).map(([st, label]) => (
              <button
                key={st}
                type="button"
                onClick={() => setMatchState(st)}
                className={`px-2.5 py-1.5 rounded-lg font-medium whitespace-nowrap cursor-pointer transition ${
                  matchState === st
                    ? 'bg-[#7667F7] text-[#F5F6FA]'
                    : 'bg-white/[0.04] text-[#9299AC] hover:text-[#F5F6FA]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {matchState === 'queuing' && (
          <Card className="p-8 text-center space-y-6">
            <div className="relative mx-auto h-20 w-20 flex items-center justify-center">
              <span className="absolute inset-0 rounded-full border border-[#7667F7]/40 animate-ping" />
              <div className="relative h-14 w-14 rounded-full bg-[#7667F7]/20 border border-[#7667F7] flex items-center justify-center">
                <Sparkles className="h-6 w-6 text-[#7667F7]" />
              </div>
            </div>
            <div>
              <h2 className="font-display text-xl font-semibold">
                Finding someone interesting...
              </h2>
              <p className="text-sm text-[#9299AC] mt-2">
                {activeTopic} · {language}
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-3 pt-2">
              <Button variant="outline" onClick={handleDeclineMatch}>
                Cancel Matching
              </Button>
              <Button
                variant="secondary"
                onClick={() => setMatchState('match_found')}
              >
                Preview Match Found
              </Button>
            </div>
          </Card>
        )}

        {(matchState === 'match_found' ||
          matchState === 'awaiting_peer_acceptance') &&
          proposal && (
            <Card className="p-6 sm:p-8 space-y-6 border-[#7667F7]/35">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[#30C48D]">Match Found</span>
                <span className="text-[#9299AC] inline-flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-[#30C48D]" />
                  Mutual acceptance required
                </span>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                <Avatar
                  name={proposal.peer.displayName}
                  src={proposal.peer.avatarUrl}
                  size="lg"
                />
                <div>
                  <h2 className="font-display text-xl font-semibold">
                    {proposal.peer.displayName}
                  </h2>
                  <p className="text-xs text-[#36B9E9] font-medium mt-0.5">
                    {proposal.peer.category} · {proposal.peer.headline}
                  </p>
                </div>
              </div>

              <div className="py-3.5 border-y border-white/[0.07]">
                <p className="text-xs text-[#9299AC] mb-1">
                  Selected Conversation Topic
                </p>
                <p className="text-sm font-medium text-[#F5F6FA]">
                  {proposal.topic}
                </p>
              </div>

              <p className="text-sm text-[#9299AC] leading-relaxed">
                {proposal.peer.bio}
              </p>

              <p className="text-xs text-[#9299AC]">
                <span className="text-[#F5F6FA] font-medium">Interests: </span>
                {proposal.peer.interests.join(' · ')}
              </p>

              {matchState === 'match_found' ? (
                <div className="grid sm:grid-cols-2 gap-3 pt-2">
                  <Button variant="outline" onClick={handleDeclineMatch}>
                    <X className="h-4 w-4" /> Decline Match
                  </Button>
                  <Button onClick={handleAcceptMatch}>
                    <CheckCircle2 className="h-4 w-4" /> Start Conversation
                  </Button>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-[#7667F7]/10 border border-[#7667F7]/30 flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 text-sm">
                    <Clock className="h-4 w-4 text-[#7667F7] shrink-0" />
                    <span>
                      Waiting for {proposal.peer.displayName} to accept...
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => onEnterChat(proposal.peer, proposal.topic)}
                  >
                    Open Text Chat
                  </Button>
                </div>
              )}
            </Card>
          )}

        {matchState === 'no_match' && (
          <StateView
            kind="no_users"
            title="No users available for these filters"
            description="Nobody is currently queued with that exact topic and audience. Broaden your filters or try Random Connect."
            actionLabel="Return to Lobby"
            onAction={() => setMatchState('idle')}
          />
        )}

        {matchState === 'timeout' && (
          <StateView
            kind="empty"
            title="Match request timed out"
            description="The proposal window expired before both participants confirmed."
            actionLabel="Search Again"
            onAction={() => setMatchState('queuing')}
          />
        )}

        {matchState === 'error' && (
          <StateView
            kind="error"
            title="Unable to reach matching queue"
            description="Connection to the matching service failed. Please retry in a moment."
            actionLabel="Back to Lobby"
            onAction={() => setMatchState('idle')}
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-white/[0.07]">
        <div>
          <p className="text-xs font-medium text-[#7667F7] mb-1">
            Connection Lobby
          </p>
          <h1 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight">
            Who would you like to meet today?
          </h1>
          <p className="text-sm text-[#9299AC] mt-1">
            Start a spontaneous conversation or match around shared interests and
            language.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 min-h-[40px] px-3.5 rounded-xl bg-[#171B29] border border-white/[0.08] text-xs">
            <Globe className="h-3.5 w-3.5 text-[#36B9E9]" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              aria-label="Preferred language"
              className="bg-transparent text-[#F5F6FA] focus:outline-none cursor-pointer"
            >
              <option value="English" className="bg-[#111522]">
                English
              </option>
              <option value="Spanish" className="bg-[#111522]">
                Spanish
              </option>
              <option value="Hindi" className="bg-[#111522]">
                Hindi
              </option>
              <option value="Mandarin" className="bg-[#111522]">
                Mandarin
              </option>
            </select>
          </div>

          <div className="flex items-center gap-2 min-h-[40px] px-3.5 rounded-xl bg-[#171B29] border border-white/[0.08] text-xs text-[#9299AC]">
            <Users className="h-3.5 w-3.5 text-[#30C48D]" />
            <span className="tabular-nums">
              {liveOnlineCount !== null
                ? `${liveOnlineCount} available`
                : 'Lobby ready · Live queue requires backend'}
            </span>
          </div>
        </div>
      </div>

      {/* Two Matching Options */}
      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="p-6 flex flex-col justify-between">
          <div className="space-y-5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#7667F7]">Random Connect</span>
              <span className="text-[#9299AC]">Spontaneous 1-on-1</span>
            </div>

            <div>
              <h2 className="font-display text-xl font-semibold">
                Meet someone unexpected
              </h2>
              <p className="text-sm text-[#9299AC] mt-1">
                Fast matching based on audience preference and language.
              </p>
            </div>

            <div>
              <span className="block text-xs font-medium text-[#9299AC] mb-2.5">
                Preferred Audience
              </span>
              <div className="grid grid-cols-3 gap-2.5">
                {(
                  ['Students', 'Professionals', 'Anyone'] as AudiencePreference[]
                ).map((aud) => (
                  <button
                    key={aud}
                    type="button"
                    onClick={() => setRandomAudience(aud)}
                    className={`min-h-[42px] px-3 rounded-xl text-xs font-medium border transition cursor-pointer ${
                      randomAudience === aud
                        ? 'bg-[#7667F7]/20 border-[#7667F7] text-[#F5F6FA]'
                        : 'bg-[#111522] border-white/[0.08] text-[#9299AC] hover:text-[#F5F6FA]'
                    }`}
                  >
                    {aud}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <Button
            size="lg"
            className="w-full mt-8"
            onClick={() => startMatching('random')}
          >
            Connect Now
          </Button>
        </Card>

        <Card className="p-6 flex flex-col justify-between border-[#36B9E9]/25">
          <div className="space-y-5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-[#36B9E9]">
                Interest Connect
              </span>
              <span className="text-[#9299AC]">Topic-aligned</span>
            </div>

            <div>
              <h2 className="font-display text-xl font-semibold">
                Match around shared interests
              </h2>
              <p className="text-sm text-[#9299AC] mt-1">
                Pick interests and a conversation topic for focused dialogue.
              </p>
            </div>

            <div>
              <span className="block text-xs font-medium text-[#9299AC] mb-2">
                Select Interests
              </span>
              <div className="flex flex-wrap gap-2">
                {INTEREST_OPTIONS.map((tag) => {
                  const active = selectedInterests.includes(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => toggleInterest(tag)}
                      className={`min-h-[36px] px-3 py-1.5 rounded-lg text-xs font-medium border transition cursor-pointer ${
                        active
                          ? 'bg-[#36B9E9]/15 border-[#36B9E9] text-[#F5F6FA]'
                          : 'bg-[#111522] border-white/[0.07] text-[#9299AC] hover:text-[#F5F6FA]'
                      }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label
                  htmlFor="lobby-topic"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Conversation Topic
                </label>
                <input
                  id="lobby-topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-xs text-[#F5F6FA] focus:outline-none focus:border-[#36B9E9]"
                />
              </div>
              <div>
                <label
                  htmlFor="lobby-aud"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Preferred Audience
                </label>
                <select
                  id="lobby-aud"
                  value={interestAudience}
                  onChange={(e) =>
                    setInterestAudience(e.target.value as AudiencePreference)
                  }
                  className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-xs text-[#F5F6FA]"
                >
                  <option value="Anyone">Anyone</option>
                  <option value="Students">Students</option>
                  <option value="Professionals">Professionals</option>
                </select>
              </div>
            </div>
          </div>

          <Button
            variant="secondary"
            size="lg"
            className="w-full mt-6"
            onClick={() => startMatching('interest')}
          >
            <RefreshCw className="h-4 w-4" /> Find Someone
          </Button>
        </Card>
      </div>
    </div>
  );
};
