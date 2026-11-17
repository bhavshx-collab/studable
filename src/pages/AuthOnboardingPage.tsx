import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, ShieldCheck, Upload } from 'lucide-react';
import {
  AccountCategory,
  AudiencePreference,
  InterestTag,
  MatchingMode,
  UserProfile,
} from '../types/domain';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Avatar } from '../components/ui/Avatar';

const ALL_INTERESTS: InterestTag[] = [
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

const CATEGORIES: { id: AccountCategory; desc: string }[] = [
  { id: 'Student', desc: 'Exploring fields, projects, and early career advice.' },
  {
    id: 'Working Professional',
    desc: 'Exchanging domain craft and expanding perspectives.',
  },
  { id: 'Entrepreneur', desc: 'Discussing ideas, product, and startup journeys.' },
  { id: 'Mentor', desc: 'Sharing experience and guiding emerging talent.' },
];

interface AuthOnboardingPageProps {
  initialMode?: 'register' | 'login';
  onComplete: (profile: UserProfile, email: string) => void;
  onBackToLanding: () => void;
}

export const AuthOnboardingPage: React.FC<AuthOnboardingPageProps> = ({
  initialMode = 'register',
  onComplete,
  onBackToLanding,
}) => {
  const [stage, setStage] = useState<'auth' | 'onboarding'>('auth');
  const [authMode, setAuthMode] = useState<'register' | 'login'>(initialMode);

  // Registration / Login state
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isAdult, setIsAdult] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Onboarding state (4 steps)
  const [step, setStep] = useState(1);
  const [highestStep, setHighestStep] = useState(1);
  const [category, setCategory] = useState<AccountCategory>('Student');
  const [avatarUrl, setAvatarUrl] = useState<string | undefined>(undefined);
  const [headline, setHeadline] = useState('');
  const [bio, setBio] = useState('');
  const [interests, setInterests] = useState<InterestTag[]>([
    'Technology',
    'Career Development',
  ]);
  const [preferredAudience, setPreferredAudience] =
    useState<AudiencePreference>('Anyone');
  const [preferredLanguage, setPreferredLanguage] = useState('English');
  const [preferredTopics, setPreferredTopics] = useState(
    'Product architecture, career growth'
  );
  const [matchingMode, setMatchingMode] = useState<MatchingMode>('interest');
  const [onboardingError, setOnboardingError] = useState<string | null>(null);

  const handleAuthSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);

    if (authMode === 'register') {
      if (!displayName.trim()) {
        setAuthError('Please enter a display name.');
        return;
      }
      if (!email.includes('@')) {
        setAuthError('Please enter a valid email address.');
        return;
      }
      if (password.length < 8) {
        setAuthError('Password must be at least 8 characters.');
        return;
      }
      if (password !== confirmPassword) {
        setAuthError('Passwords do not match.');
        return;
      }
      if (!isAdult || !acceptedTerms) {
        setAuthError(
          'You must confirm that you are 18+ and accept the Terms & Privacy Policy.'
        );
        return;
      }
      setStage('onboarding');
    } else {
      if (!email.includes('@') || !password) {
        setAuthError('Enter your email and password to sign in.');
        return;
      }
      onComplete(
        {
          id: 'usr_self',
          displayName: displayName.trim() || 'Aarav Mehta',
          category: 'Working Professional',
          headline: 'Product Engineer · Distributed Systems',
          bio: 'Returning member ready for thoughtful 1-on-1 conversations.',
          skills: ['TypeScript', 'Python', 'System Design'],
          interests: ['Technology', 'AI and Machine Learning', 'Startups'],
          languages: ['English'],
          connectionCount: 18,
          isVerified: true,
        },
        email.trim()
      );
    }
  };

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setAvatarUrl(reader.result);
      }
    };
    reader.readAsDataURL(file);
  };

  const toggleInterest = (tag: InterestTag) => {
    setInterests((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const goToStep = (next: number) => {
    setOnboardingError(null);
    if (step === 2 && next > 2 && !displayName.trim()) {
      setOnboardingError('Please enter your display name to continue.');
      return;
    }
    if (step === 3 && next > 3 && interests.length === 0) {
      setOnboardingError('Select at least one interest to personalize matches.');
      return;
    }
    setStep(next);
    setHighestStep((prev) => Math.max(prev, next));
  };

  if (stage === 'auth') {
    return (
      <div className="min-h-screen bg-[#0B0D14] flex flex-col justify-center px-4 py-12">
        <div className="max-w-md w-full mx-auto">
          <button
            type="button"
            onClick={onBackToLanding}
            className="min-h-[40px] inline-flex items-center gap-1.5 text-xs font-medium text-[#9299AC] hover:text-[#F5F6FA] mb-4 cursor-pointer"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Valence
          </button>

          <Card className="p-6 sm:p-8">
            <div className="mb-6">
              <h1 className="font-display text-2xl font-semibold">
                {authMode === 'register' ? 'Create your account' : 'Welcome back'}
              </h1>
              <p className="text-sm text-[#9299AC] mt-1.5">
                {authMode === 'register'
                  ? 'Set up your Valence profile in four quick steps.'
                  : 'Sign in to resume your connections and conversations.'}
              </p>
            </div>

            {authError && (
              <div
                role="alert"
                className="mb-5 p-3.5 rounded-xl bg-[#F16C79]/10 border border-[#F16C79]/35 text-xs text-[#F16C79]"
              >
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              {authMode === 'register' && (
                <div>
                  <label
                    htmlFor="reg-name"
                    className="block text-xs font-medium text-[#9299AC] mb-1.5"
                  >
                    Display Name
                  </label>
                  <input
                    id="reg-name"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="e.g., Maya Lin"
                    className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7]"
                  />
                </div>
              )}

              <div>
                <label
                  htmlFor="auth-email"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Email Address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@domain.com"
                  className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7]"
                />
              </div>

              <div>
                <label
                  htmlFor="auth-pass"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Password
                </label>
                <input
                  id="auth-pass"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7]"
                />
              </div>

              {authMode === 'register' && (
                <>
                  <div>
                    <label
                      htmlFor="auth-confirm"
                      className="block text-xs font-medium text-[#9299AC] mb-1.5"
                    >
                      Confirm Password
                    </label>
                    <input
                      id="auth-confirm"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7]"
                    />
                  </div>

                  <label className="flex items-start gap-2.5 text-xs text-[#9299AC] cursor-pointer pt-1">
                    <input
                      type="checkbox"
                      checked={isAdult}
                      onChange={(e) => setIsAdult(e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-[#7667F7]"
                    />
                    <span>I confirm that I am 18 years of age or older.</span>
                  </label>

                  <label className="flex items-start gap-2.5 text-xs text-[#9299AC] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={acceptedTerms}
                      onChange={(e) => setAcceptedTerms(e.target.checked)}
                      className="mt-0.5 h-4 w-4 accent-[#7667F7]"
                    />
                    <span>
                      I accept the Terms of Service and Privacy Policy, and agree to
                      keep conversations respectful.
                    </span>
                  </label>
                </>
              )}

              <Button type="submit" className="w-full mt-2">
                {authMode === 'register' ? 'Create Account' : 'Sign In'}
              </Button>
            </form>

            <div className="my-5 flex items-center gap-3">
              <div className="h-px flex-1 bg-white/[0.07]" />
              <span className="text-[11px] text-[#9299AC]">OR</span>
              <div className="h-px flex-1 bg-white/[0.07]" />
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled
              title="Optional future Google OAuth integration"
            >
              Continue with Google (Future Integration)
            </Button>

            <p className="text-xs text-center text-[#9299AC] mt-6">
              {authMode === 'register'
                ? 'Already have an account?'
                : 'New to Valence?'}{' '}
              <button
                type="button"
                onClick={() => {
                  setAuthError(null);
                  setAuthMode(authMode === 'register' ? 'login' : 'register');
                }}
                className="text-[#36B9E9] hover:underline font-medium cursor-pointer"
              >
                {authMode === 'register' ? 'Log in' : 'Create account'}
              </button>
            </p>
          </Card>
        </div>
      </div>
    );
  }

  // 4-Step Onboarding
  return (
    <div className="min-h-screen bg-[#0B0D14] px-4 py-10 flex flex-col justify-center">
      <div className="max-w-2xl w-full mx-auto">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="font-mono text-[#36B9E9]">Step {step} of 4</span>
            <span className="text-[#9299AC]">
              {step === 1 && 'Identity'}
              {step === 2 && 'Personal Information'}
              {step === 3 && 'Interests'}
              {step === 4 && 'Conversation Preferences'}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map((s) => {
              const unlocked = s <= highestStep;
              return (
                <button
                  key={s}
                  type="button"
                  disabled={!unlocked}
                  onClick={() => unlocked && setStep(s)}
                  aria-label={`Go to onboarding step ${s}`}
                  className={`h-2.5 rounded-full transition-all ${
                    s <= step
                      ? 'bg-[#7667F7] cursor-pointer'
                      : unlocked
                      ? 'bg-[#7667F7]/35 cursor-pointer'
                      : 'bg-white/10 cursor-not-allowed'
                  }`}
                />
              );
            })}
          </div>
        </div>

        <Card className="p-6 sm:p-8">
          {onboardingError && (
            <div
              role="alert"
              className="mb-5 p-3 rounded-xl bg-[#F16C79]/10 border border-[#F16C79]/35 text-xs text-[#F16C79]"
            >
              {onboardingError}
            </div>
          )}

          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h2 className="font-display text-xl font-semibold">
                  Choose your identity
                </h2>
                <p className="text-sm text-[#9299AC] mt-1">
                  This helps others understand your perspective before starting a
                  conversation.
                </p>
              </div>
              <div className="grid sm:grid-cols-2 gap-3.5">
                {CATEGORIES.map((c) => {
                  const selected = category === c.id;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setCategory(c.id)}
                      className={`p-4 rounded-xl border text-left transition cursor-pointer ${
                        selected
                          ? 'bg-[#7667F7]/15 border-[#7667F7]'
                          : 'bg-[#111522] border-white/[0.07] hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm text-[#F5F6FA]">
                          {c.id}
                        </span>
                        {selected && <Check className="h-4 w-4 text-[#7667F7]" />}
                      </div>
                      <p className="text-xs text-[#9299AC] mt-1.5 leading-relaxed">
                        {c.desc}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-xl font-semibold">
                  Personal information
                </h2>
                <p className="text-sm text-[#9299AC] mt-1">
                  Private account details like your email are never shown to matches.
                </p>
              </div>

              <div className="flex items-center gap-4 pt-1">
                <Avatar
                  name={displayName || 'New Member'}
                  src={avatarUrl}
                  size="lg"
                />
                <div>
                  <label className="inline-flex items-center gap-2 min-h-[40px] px-4 py-2 rounded-xl bg-[#111522] border border-white/12 hover:border-white/25 text-xs font-medium text-[#F5F6FA] cursor-pointer">
                    <Upload className="h-3.5 w-3.5" />
                    <span>Upload Profile Picture</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleAvatarUpload}
                      className="sr-only"
                    />
                  </label>
                  <p className="text-[11px] text-[#9299AC] mt-1.5">
                    Optional · JPG or PNG
                  </p>
                </div>
              </div>

              <div>
                <label
                  htmlFor="onb-name"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Display Name
                </label>
                <input
                  id="onb-name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7]"
                />
              </div>

              <div>
                <label
                  htmlFor="onb-headline"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Education or Profession
                </label>
                <input
                  id="onb-headline"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder="e.g., B.S. Computer Science or Staff Product Designer"
                  className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] focus:outline-none focus:border-[#7667F7]"
                />
              </div>

              <div>
                <label
                  htmlFor="onb-bio"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Short Biography
                </label>
                <textarea
                  id="onb-bio"
                  rows={3}
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  placeholder="What are you curious about or building right now?"
                  className="w-full p-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA] resize-none focus:outline-none focus:border-[#7667F7]"
                />
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="font-display text-xl font-semibold">
                  Select your interests
                </h2>
                <p className="text-sm text-[#9299AC] mt-1">
                  Choose topics you want to explore in 1-on-1 conversations.
                </p>
              </div>
              <div className="flex flex-wrap gap-2.5">
                {ALL_INTERESTS.map((tag) => {
                  const active = interests.includes(tag);
                  return (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => toggleInterest(tag)}
                      className={`min-h-[40px] px-4 py-2 rounded-xl text-xs font-medium border transition cursor-pointer ${
                        active
                          ? 'bg-[#7667F7]/20 border-[#7667F7] text-[#F5F6FA]'
                          : 'bg-[#111522] border-white/[0.08] text-[#9299AC] hover:text-[#F5F6FA]'
                      }`}
                    >
                      {tag}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div>
                <h2 className="font-display text-xl font-semibold">
                  Conversation preferences
                </h2>
                <p className="text-sm text-[#9299AC] mt-1">
                  Set defaults for your matching lobby. You can adjust these anytime.
                </p>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="onb-aud"
                    className="block text-xs font-medium text-[#9299AC] mb-1.5"
                  >
                    Preferred Audience
                  </label>
                  <select
                    id="onb-aud"
                    value={preferredAudience}
                    onChange={(e) =>
                      setPreferredAudience(e.target.value as AudiencePreference)
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
                    htmlFor="onb-lang"
                    className="block text-xs font-medium text-[#9299AC] mb-1.5"
                  >
                    Preferred Language
                  </label>
                  <select
                    id="onb-lang"
                    value={preferredLanguage}
                    onChange={(e) => setPreferredLanguage(e.target.value)}
                    className="w-full h-11 px-3 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
                  >
                    <option value="English">English</option>
                    <option value="Spanish">Spanish</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Mandarin">Mandarin</option>
                  </select>
                </div>
              </div>

              <div>
                <label
                  htmlFor="onb-topics"
                  className="block text-xs font-medium text-[#9299AC] mb-1.5"
                >
                  Preferred Topics
                </label>
                <input
                  id="onb-topics"
                  value={preferredTopics}
                  onChange={(e) => setPreferredTopics(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-xl bg-[#0B0D14] border border-white/10 text-sm text-[#F5F6FA]"
                />
              </div>

              <div>
                <span className="block text-xs font-medium text-[#9299AC] mb-2">
                  Default Matching Mode
                </span>
                <div className="grid grid-cols-2 gap-3">
                  {(['random', 'interest'] as MatchingMode[]).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMatchingMode(m)}
                      className={`min-h-[44px] p-3 rounded-xl border text-left text-xs font-medium cursor-pointer transition ${
                        matchingMode === m
                          ? 'bg-[#36B9E9]/15 border-[#36B9E9] text-[#F5F6FA]'
                          : 'bg-[#111522] border-white/[0.08] text-[#9299AC]'
                      }`}
                    >
                      {m === 'random'
                        ? 'Random Matching'
                        : 'Interest-Based Matching'}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-[#9299AC] pt-1">
                <ShieldCheck className="h-4 w-4 text-[#30C48D] shrink-0" />
                <span>
                  Valence MVP focuses on safe, distraction-free text conversations.
                </span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-6 mt-6 border-t border-white/[0.07]">
            <Button
              type="button"
              variant="ghost"
              disabled={step === 1}
              onClick={() => setStep((s) => Math.max(1, s - 1))}
            >
              <ArrowLeft className="h-4 w-4" /> Previous
            </Button>

            {step < 4 ? (
              <Button type="button" onClick={() => goToStep(step + 1)}>
                Continue <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="button"
                onClick={() =>
                  onComplete(
                    {
                      id: 'usr_self',
                      displayName: displayName.trim() || 'New Member',
                      avatarUrl,
                      category,
                      headline: headline.trim() || `${category} on Valence`,
                      bio:
                        bio.trim() ||
                        'Curious to exchange ideas and learn from new perspectives.',
                      skills: [],
                      interests,
                      languages: [preferredLanguage],
                      connectionCount: 0,
                      isVerified: true,
                    },
                    email.trim() || 'member@valence.app'
                  )
                }
              >
                Enter Valence <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
