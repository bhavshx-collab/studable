import React, { useState } from 'react';
import {
  Ban,
  CheckCircle2,
  Flag,
  Globe,
  MessageSquare,
  UserPlus,
} from 'lucide-react';
import { UserProfile } from '../types/domain';
import { Avatar } from '../components/ui/Avatar';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';

interface ProfilePageProps {
  profile: UserProfile;
  isOwnProfile: boolean;
  isConnected?: boolean;
  isPending?: boolean;
  onMessage?: () => void;
  onConnect?: () => void;
  onBlock?: (user: UserProfile) => void;
  onReport?: (user: UserProfile, reason: string) => void;
  onEditProfile?: () => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  profile,
  isOwnProfile,
  isConnected = false,
  isPending = false,
  onMessage,
  onConnect,
  onBlock,
  onReport,
  onEditProfile,
}) => {
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState('Inappropriate profile content');
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <div className="space-y-6 max-w-3xl">
      {notice && (
        <div className="p-3.5 rounded-xl bg-[#30C48D]/10 border border-[#30C48D]/30 text-xs text-[#30C48D]">
          {notice}
        </div>
      )}

      <Card className="p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="flex items-center gap-4">
            <Avatar
              name={profile.displayName}
              src={profile.avatarUrl}
              size="xl"
            />
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="font-display text-2xl font-semibold">
                  {profile.displayName}
                </h1>
                {profile.isVerified && (
                  <CheckCircle2
                    className="h-4 w-4 text-[#30C48D]"
                    aria-label="Verified profile"
                  />
                )}
              </div>
              <p className="text-sm text-[#9299AC] mt-1">
                {profile.category} · {profile.headline}
              </p>
              <p className="text-xs text-[#36B9E9] mt-1.5 font-medium tabular-nums">
                {profile.connectionCount} Connections
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {isOwnProfile ? (
              <Button variant="outline" onClick={onEditProfile}>
                Edit Profile
              </Button>
            ) : (
              <>
                {isConnected ? (
                  <Button onClick={onMessage}>
                    <MessageSquare className="h-4 w-4" /> Message
                  </Button>
                ) : (
                  <Button disabled={isPending} onClick={onConnect}>
                    <UserPlus className="h-4 w-4" />
                    {isPending ? 'Request Pending' : 'Connect'}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setReportOpen(true)}
                >
                  <Flag className="h-4 w-4 text-[#F16C79]" /> Report
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    onBlock?.(profile);
                    setNotice(`${profile.displayName} has been blocked.`);
                  }}
                >
                  <Ban className="h-4 w-4 text-[#F16C79]" /> Block
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="text-xs font-semibold text-[#9299AC]">About Me</h2>
        <p className="text-sm text-[#F5F6FA] leading-relaxed">{profile.bio}</p>
      </Card>

      <div className="grid sm:grid-cols-2 gap-5">
        <Card className="space-y-3">
          <h2 className="text-xs font-semibold text-[#9299AC]">Skills</h2>
          {profile.skills.length > 0 ? (
            <p className="text-sm text-[#F5F6FA] leading-relaxed">
              {profile.skills.join(' · ')}
            </p>
          ) : (
            <p className="text-xs text-[#9299AC]">No skills listed yet.</p>
          )}
        </Card>

        <Card className="space-y-3">
          <h2 className="text-xs font-semibold text-[#9299AC]">Interests</h2>
          <p className="text-sm text-[#F5F6FA] leading-relaxed">
            {profile.interests.join(' · ')}
          </p>
        </Card>
      </div>

      <Card className="flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-sm">
          <Globe className="h-4 w-4 text-[#36B9E9]" />
          <span className="font-medium">Languages</span>
        </div>
        <span className="text-sm text-[#9299AC]">
          {profile.languages.join(' · ')}
        </span>
      </Card>

      <Modal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title={`Report ${profile.displayName}`}
        description="Private details remain protected. Our moderation team reviews all reports."
      >
        <div className="space-y-4">
          <select
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value)}
            className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
          >
            <option>Inappropriate profile content</option>
            <option>Spam or promotional links</option>
            <option>Impersonation</option>
          </select>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setReportOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                onReport?.(profile, reportReason);
                setReportOpen(false);
                setNotice('Report submitted for moderation review.');
              }}
            >
              Submit Report
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
