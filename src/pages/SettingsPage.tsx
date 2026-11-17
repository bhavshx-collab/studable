import React, { useState } from 'react';
import { LogOut, ShieldAlert, Trash2 } from 'lucide-react';
import {
  AccountCategory,
  OwnAccountSettings,
  UserProfile,
} from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';

interface SettingsPageProps {
  profile: UserProfile;
  settings: OwnAccountSettings;
  blockedUsers: UserProfile[];
  onSaveProfileAndSettings: (
    updatedProfile: UserProfile,
    updatedSettings: OwnAccountSettings
  ) => void;
  onUnblockUser: (userId: string) => void;
  onLogout: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  profile,
  settings: initialSettings,
  blockedUsers,
  onSaveProfileAndSettings,
  onUnblockUser,
  onLogout,
}) => {
  const [displayName, setDisplayName] = useState(profile.displayName);
  const [category, setCategory] = useState<AccountCategory>(profile.category);
  const [headline, setHeadline] = useState(profile.headline);
  const [bio, setBio] = useState(profile.bio);
  const [settings, setSettings] = useState(initialSettings);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveProfileAndSettings(
      {
        ...profile,
        displayName: displayName.trim() || profile.displayName,
        category,
        headline: headline.trim() || profile.headline,
        bio: bio.trim() || profile.bio,
      },
      settings
    );
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2600);
  };

  const handlePasswordChange = () => {
    if (!currentPassword || newPassword.length < 8) {
      setPasswordNotice(
        'Enter your current password and a new password of at least 8 characters.'
      );
      return;
    }
    setCurrentPassword('');
    setNewPassword('');
    setPasswordNotice('Password updated for this session.');
  };

  return (
    <form onSubmit={save} className="space-y-6 max-w-3xl">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-white/[0.07]">
        <div>
          <h1 className="font-display text-2xl font-semibold">
            Settings &amp; Privacy
          </h1>
          <p className="text-sm text-[#9299AC] mt-1">
            Manage your profile, matching defaults, privacy controls, and
            security.
          </p>
        </div>
        <Button type="submit">Save Changes</Button>
      </div>

      {savedNotice && (
        <div className="p-3.5 rounded-xl bg-[#30C48D]/10 border border-[#30C48D]/30 text-xs text-[#30C48D]">
          Profile and preferences saved.
        </div>
      )}

      {/* Edit Profile & Account Preferences */}
      <Card className="space-y-4">
        <h2 className="text-sm font-semibold">
          Edit Profile &amp; Account Preferences
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="set-name"
              className="block text-xs text-[#9299AC] mb-1.5"
            >
              Display Name
            </label>
            <input
              id="set-name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            />
          </div>
          <div>
            <label
              htmlFor="set-cat"
              className="block text-xs text-[#9299AC] mb-1.5"
            >
              Identity Category
            </label>
            <select
              id="set-cat"
              value={category}
              onChange={(e) => setCategory(e.target.value as AccountCategory)}
              className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            >
              <option value="Student">Student</option>
              <option value="Working Professional">Working Professional</option>
              <option value="Entrepreneur">Entrepreneur</option>
              <option value="Mentor">Mentor</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="set-headline"
              className="block text-xs text-[#9299AC] mb-1.5"
            >
              Education or Profession
            </label>
            <input
              id="set-headline"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            />
          </div>
          <div>
            <label
              htmlFor="set-email"
              className="block text-xs text-[#9299AC] mb-1.5"
            >
              Email (Private)
            </label>
            <input
              id="set-email"
              value={settings.email}
              onChange={(e) =>
                setSettings({ ...settings, email: e.target.value })
              }
              className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            />
          </div>
        </div>
        <div>
          <label
            htmlFor="set-bio"
            className="block text-xs text-[#9299AC] mb-1.5"
          >
            Biography
          </label>
          <textarea
            id="set-bio"
            rows={3}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            className="w-full p-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] resize-none"
          />
        </div>
      </Card>

      {/* Matching & Language Preferences */}
      <Card className="space-y-4">
        <h2 className="text-sm font-semibold">
          Matching &amp; Language Preferences
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="set-aud"
              className="block text-xs text-[#9299AC] mb-1.5"
            >
              Preferred Audience
            </label>
            <select
              id="set-aud"
              value={settings.preferredAudience}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  preferredAudience: e.target
                    .value as OwnAccountSettings['preferredAudience'],
                })
              }
              className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            >
              <option value="Anyone">Anyone</option>
              <option value="Students">Students</option>
              <option value="Professionals">Professionals</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="set-lang"
              className="block text-xs text-[#9299AC] mb-1.5"
            >
              Preferred Language
            </label>
            <select
              id="set-lang"
              value={settings.preferredLanguage}
              onChange={(e) =>
                setSettings({ ...settings, preferredLanguage: e.target.value })
              }
              className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
            >
              <option value="English">English</option>
              <option value="Hindi">Hindi</option>
              <option value="Spanish">Spanish</option>
              <option value="Mandarin">Mandarin</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Privacy & Notifications */}
      <Card className="space-y-2">
        <h2 className="text-sm font-semibold mb-2">
          Privacy &amp; Notification Settings
        </h2>
        {[
          {
            key: 'allowRandomDiscovery' as const,
            label: 'Allow spontaneous Random Connect discovery',
          },
          {
            key: 'showOnlineStatus' as const,
            label: 'Show availability status to accepted connections',
          },
          {
            key: 'notifyConnectionRequests' as const,
            label: 'Notify on new connection requests',
          },
          {
            key: 'notifyMessages' as const,
            label: 'Notify on new messages',
          },
        ].map((item) => (
          <label
            key={item.key}
            className="flex items-center justify-between py-3 border-b border-white/[0.06] last:border-0 text-sm cursor-pointer"
          >
            <span className="text-[#F5F6FA]">{item.label}</span>
            <input
              type="checkbox"
              checked={settings[item.key]}
              onChange={(e) =>
                setSettings({ ...settings, [item.key]: e.target.checked })
              }
              className="h-4 w-4 accent-[#7667F7]"
            />
          </label>
        ))}
      </Card>

      {/* Blocked Users */}
      <Card className="space-y-3">
        <h2 className="text-sm font-semibold">Blocked Users</h2>
        {blockedUsers.length === 0 ? (
          <p className="text-xs text-[#9299AC]">
            You have not blocked any members.
          </p>
        ) : (
          <div className="divide-y divide-white/[0.06]">
            {blockedUsers.map((u) => (
              <div
                key={u.id}
                className="flex items-center justify-between py-2.5 text-xs"
              >
                <span className="text-[#F5F6FA]">
                  {u.displayName} ·{' '}
                  <span className="text-[#9299AC]">{u.category}</span>
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => onUnblockUser(u.id)}
                >
                  Unblock
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Change Password & Account Actions */}
      <Card className="space-y-4 border-[#F16C79]/20">
        <h2 className="text-sm font-semibold">
          Change Password &amp; Account Actions
        </h2>
        <div className="grid sm:grid-cols-3 gap-3">
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Current password"
            className="h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password (8+ chars)"
            className="h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
          />
          <Button type="button" variant="outline" onClick={handlePasswordChange}>
            Update Password
          </Button>
        </div>
        {passwordNotice && (
          <p className="text-xs text-[#36B9E9]">{passwordNotice}</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-white/[0.06]">
          <Button type="button" variant="outline" onClick={onLogout}>
            <LogOut className="h-4 w-4" /> Logout
          </Button>
          <Button
            type="button"
            variant="danger"
            onClick={() => setDeleteModalOpen(true)}
          >
            <Trash2 className="h-4 w-4" /> Delete Account
          </Button>
        </div>
      </Card>

      <Modal
        open={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Delete your Valence account?"
        description="This permanently removes your profile, connections, and conversation history."
      >
        <div className="flex items-center gap-2 text-xs text-[#F16C79] mb-4">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span>This action cannot be undone.</span>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setDeleteModalOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onLogout}>
            Confirm Deletion
          </Button>
        </div>
      </Modal>
    </form>
  );
};
