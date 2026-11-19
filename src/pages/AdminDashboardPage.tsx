import React, { useState } from 'react';
import {
  ArrowLeft,
  Ban,
  CheckCircle,
  Search,
  Shield,
  Users,
} from 'lucide-react';
import { ModerationReport, UserProfile } from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

interface AdminDashboardPageProps {
  reports: ModerationReport[];
  users: UserProfile[];
  onUpdateReportStatus: (
    reportId: string,
    status: ModerationReport['status']
  ) => void;
  onExitAdmin: () => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({
  reports,
  users,
  onUpdateReportStatus,
  onExitAdmin,
}) => {
  const [query, setQuery] = useState('');
  const [suspendedIds, setSuspendedIds] = useState<string[]>([]);
  const [history, setHistory] = useState<string[]>([
    'Issued formal warning to Dev P. (rep_900) · Yesterday',
  ]);

  const handleReportAction = (
    report: ModerationReport,
    action: 'resolved_suspended' | 'dismissed'
  ) => {
    onUpdateReportStatus(report.id, action);
    if (action === 'resolved_suspended') {
      setSuspendedIds((prev) =>
        prev.includes(report.reportedUserId)
          ? prev
          : [...prev, report.reportedUserId]
      );
      setHistory((prev) => [
        `Suspended ${report.reportedUserName} (${report.id}) · Just now`,
        ...prev,
      ]);
    } else {
      setHistory((prev) => [
        `Dismissed report ${report.id} · Just now`,
        ...prev,
      ]);
    }
  };

  const toggleUserSuspension = (user: UserProfile) => {
    const isSuspended = suspendedIds.includes(user.id);
    setSuspendedIds((prev) =>
      isSuspended ? prev.filter((id) => id !== user.id) : [...prev, user.id]
    );
    setHistory((prev) => [
      `${isSuspended ? 'Unsuspended' : 'Suspended'} ${user.displayName} · Just now`,
      ...prev,
    ]);
  };

  const filteredUsers = users.filter(
    (u) =>
      u.displayName.toLowerCase().includes(query.toLowerCase()) ||
      u.category.toLowerCase().includes(query.toLowerCase())
  );

  const pendingCount = reports.filter((r) => r.status === 'pending').length;

  return (
    <div className="min-h-screen bg-[#0B0D14] text-[#F5F6FA]">
      {/* Isolated Admin Top Bar */}
      <header className="border-b border-white/[0.08] bg-[#111522] px-4 sm:px-8 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-8 w-8 rounded-lg bg-[#F16C79]/15 border border-[#F16C79]/30 flex items-center justify-center shrink-0">
            <Shield className="h-4 w-4 text-[#F16C79]" />
          </div>
          <span className="font-display font-semibold text-sm truncate">
            Studable Trust &amp; Safety Console
          </span>
          <span className="hidden md:inline text-xs text-[#9299AC]">
            · Isolated Administrator Workspace
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={onExitAdmin}>
          <ArrowLeft className="h-3.5 w-3.5" /> Exit Admin
        </Button>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-8 py-8 space-y-8">
        {/* Metrics */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { label: 'Total Registered Users', value: '1,420' },
            { label: 'Active Users (24h)', value: '312' },
            { label: 'Total Matches', value: '4,890' },
            { label: 'Total Conversations', value: '3,742' },
            {
              label: 'Pending Reports',
              value: String(pendingCount),
              alert: pendingCount > 0,
            },
          ].map((m) => (
            <Card key={m.label} className="p-4">
              <p className="text-xs text-[#9299AC]">{m.label}</p>
              <p
                className={`font-mono text-2xl font-semibold mt-2 tabular-nums ${
                  m.alert ? 'text-[#F16C79]' : 'text-[#F5F6FA]'
                }`}
              >
                {m.value}
              </p>
            </Card>
          ))}
        </div>

        <div className="grid lg:grid-cols-12 gap-6">
          {/* Report Management Queue */}
          <div className="lg:col-span-7 space-y-4">
            <h2 className="text-base font-semibold">Report Management Queue</h2>
            {reports.map((rep) => (
              <Card key={rep.id} className="space-y-3 p-5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-semibold">{rep.reportedUserName}</span>
                    <span
                      className={`text-xs font-medium ${
                        rep.status === 'pending'
                          ? 'text-[#F16C79]'
                          : 'text-[#30C48D]'
                      }`}
                    >
                      · {rep.status.replace('_', ' ')}
                    </span>
                  </div>
                  <span className="font-mono text-xs text-[#9299AC] tabular-nums">
                    {rep.createdAt}
                  </span>
                </div>
                <p className="text-xs font-medium text-[#F5F6FA]">{rep.reason}</p>
                <p className="text-xs text-[#9299AC] leading-relaxed">
                  {rep.details}
                </p>
                {rep.status === 'pending' && (
                  <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.06]">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleReportAction(rep, 'dismissed')}
                    >
                      <CheckCircle className="h-3.5 w-3.5" /> Dismiss
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() =>
                        handleReportAction(rep, 'resolved_suspended')
                      }
                    >
                      <Ban className="h-3.5 w-3.5" /> Suspend User
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>

          {/* User Search + Moderation History */}
          <div className="lg:col-span-5 space-y-6">
            <Card className="space-y-4 p-5">
              <h2 className="text-base font-semibold flex items-center gap-2">
                <Users className="h-4 w-4 text-[#36B9E9]" /> User Search &amp;
                Suspension
              </h2>
              <div className="relative">
                <Search className="h-4 w-4 text-[#9299AC] absolute left-3.5 top-3.5" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by name or category..."
                  aria-label="Search users"
                  className="w-full h-11 pl-10 pr-3 rounded-xl bg-[#0B0D14] border border-white/10 text-xs text-[#F5F6FA]"
                />
              </div>
              <div className="divide-y divide-white/[0.06]">
                {filteredUsers.length === 0 ? (
                  <p className="text-xs text-[#9299AC] py-3">
                    No users match that search.
                  </p>
                ) : (
                  filteredUsers.map((u) => {
                    const isSuspended = suspendedIds.includes(u.id);
                    return (
                      <div
                        key={u.id}
                        className="flex items-center justify-between py-2.5 text-xs gap-3"
                      >
                        <div className="min-w-0">
                          <p className="font-medium truncate">{u.displayName}</p>
                          <p className="text-[#9299AC] truncate">{u.category}</p>
                        </div>
                        <Button
                          size="sm"
                          variant={isSuspended ? 'outline' : 'danger'}
                          onClick={() => toggleUserSuspension(u)}
                        >
                          {isSuspended ? 'Unsuspend' : 'Suspend'}
                        </Button>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>

            <Card className="space-y-3 p-5">
              <h2 className="text-sm font-semibold">Moderation History</h2>
              <ul className="divide-y divide-white/[0.06] text-xs text-[#9299AC]">
                {history.map((entry, idx) => (
                  <li key={idx} className="py-2.5 first:pt-0 last:pb-0">
                    {entry}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};
