import React from 'react';
import { ShieldAlert, ArrowLeft, KeyRound } from 'lucide-react';
import { UserProfile } from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

interface AdminGuardProps {
  currentUser: UserProfile;
  children: React.ReactNode;
  onNavigateHome: () => void;
  onSimulateAdminAccess?: () => void;
}

export const AdminGuard: React.FC<AdminGuardProps> = ({
  currentUser,
  children,
  onNavigateHome,
  onSimulateAdminAccess,
}) => {
  const isAdmin = currentUser.role === 'admin';

  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-[#0B0D14] flex flex-col justify-center items-center px-4 py-12 text-[#F5F6FA]">
        <Card className="max-w-md w-full p-8 border-[#F16C79]/30 bg-[#111522] text-center space-y-6">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-[#F16C79]/15 border border-[#F16C79]/30 flex items-center justify-center">
            <ShieldAlert className="h-7 w-7 text-[#F16C79]" />
          </div>

          <div className="space-y-2">
            <h1 className="font-display text-xl font-semibold">
              Administrator Access Restricted
            </h1>
            <p className="text-sm text-[#9299AC] leading-relaxed">
              The Studable Trust &amp; Safety Console is restricted to verified platform administrators.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#171B29] border border-white/[0.08] text-xs text-left text-[#9299AC] space-y-1.5">
            <div className="font-semibold text-[#F5F6FA] flex items-center gap-1.5">
              <span>Security Note:</span>
            </div>
            <p>
              This is a client-side authorization guard. Production backend authorization (JWT claim verification and role checks at the API gateway) is required and specified in the backend architecture for Phase 1 and Phase 7.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2 justify-center">
            <Button variant="outline" onClick={onNavigateHome}>
              <ArrowLeft className="h-4 w-4" /> Return to Safety
            </Button>
            {onSimulateAdminAccess && (
              <Button variant="secondary" onClick={onSimulateAdminAccess}>
                <KeyRound className="h-4 w-4" /> Simulate Admin Session
              </Button>
            )}
          </div>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
};
