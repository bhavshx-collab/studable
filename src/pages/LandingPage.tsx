import React, { useState } from 'react';
import {
  ArrowRight,
  Compass,
  Lock,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Users,
  Zap,
} from 'lucide-react';
import { HERO_ILLUSTRATION_URL } from '../data/prototypeMocks';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

interface LandingPageProps {
  onStartConnecting: () => void;
  onLogin: () => void;
  onOpenAdminPreview: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onStartConnecting,
  onLogin,
  onOpenAdminPreview,
}) => {
  const [heroImgError, setHeroImgError] = useState(false);

  const scrollToHowItWorks = () => {
    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#0B0D14] text-[#F5F6FA]">
      {/* Strict 3-Zone Top Bar */}
      <header className="sticky top-0 z-30 glass-surface border-b border-white/[0.07]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-8">
          <a
            href="#top"
            className="font-display text-lg font-bold tracking-tight text-[#F5F6FA] whitespace-nowrap shrink-0"
          >
            Valence
          </a>

          <nav className="hidden md:flex items-center gap-7 text-sm font-medium text-[#9299AC]">
            <a
              href="#how-it-works"
              className="hover:text-[#F5F6FA] hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
            >
              How It Works
            </a>
            <a
              href="#ways-to-connect"
              className="hover:text-[#F5F6FA] hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
            >
              Ways to Connect
            </a>
            <a
              href="#safety"
              className="hover:text-[#F5F6FA] hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
            >
              Safety
            </a>
            <button
              type="button"
              onClick={onLogin}
              className="hover:text-[#F5F6FA] hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              Sign In
            </button>
          </nav>

          <div className="shrink-0">
            <Button size="sm" onClick={onStartConnecting}>
              Start Connecting
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section id="top" className="pt-14 pb-20 sm:pt-20 sm:pb-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-10 lg:gap-12 items-stretch">
          <div className="lg:col-span-6 flex flex-col justify-center space-y-6">
            <p className="text-xs font-medium tracking-wide text-[#36B9E9]">
              Real-Time Social &amp; Professional Connection
            </p>
            <h1 className="font-display text-[clamp(2.25rem,4vw,3.5rem)] font-semibold tracking-tight leading-[1.1] text-[#F5F6FA]">
              Meet People. Share Ideas. Grow Together.
            </h1>
            <p className="text-base sm:text-lg text-[#9299AC] leading-relaxed max-w-xl">
              Discover new people, exchange knowledge and build meaningful connections
              beyond your existing network.
            </p>

            <div className="flex flex-wrap items-center gap-3.5 pt-2">
              <Button size="lg" onClick={onStartConnecting}>
                Start Connecting
                <ArrowRight className="h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" onClick={scrollToHowItWorks}>
                Explore How It Works
              </Button>
            </div>

            <div className="pt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-[#9299AC] border-t border-white/[0.07]">
              <span>Mutual match acceptance</span>
              <span aria-hidden="true">·</span>
              <span>Privacy-protected profiles</span>
              <span aria-hidden="true">·</span>
              <span>Text-first 1-on-1 conversations</span>
            </div>
          </div>

          <div className="lg:col-span-6 flex">
            <div className="relative w-full rounded-2xl bg-[#111522] border border-white/[0.08] overflow-hidden min-h-[300px] lg:min-h-[420px]">
              {!heroImgError ? (
                <img
                  src={HERO_ILLUSTRATION_URL}
                  alt="Abstract network of students, builders, entrepreneurs, and mentors connected through meaningful conversations"
                  referrerPolicy="no-referrer"
                  onError={() => setHeroImgError(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-gradient-to-br from-[#111522] via-[#171B29] to-[#0B0D14] text-center">
                  <Sparkles className="h-8 w-8 text-[#7667F7] mb-3" />
                  <p className="text-sm font-medium text-[#F5F6FA]">
                    Find someone worth talking to
                  </p>
                  <p className="text-xs text-[#9299AC] mt-1">
                    Spontaneous and interest-aligned 1-on-1 connections
                  </p>
                </div>
              )}
              <div className="absolute inset-x-0 bottom-0 p-5 bg-gradient-to-t from-[#0B0D14]/90 via-[#0B0D14]/50 to-transparent">
                <p className="text-xs text-[#F5F6FA] font-medium">
                  Find someone worth talking to — students, professionals, founders, and mentors.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 1. How It Works */}
      <section
        id="how-it-works"
        className="py-20 border-t border-white/[0.06] bg-[#111522]/45"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="max-w-2xl mb-12">
            <p className="text-xs font-medium tracking-wide text-[#36B9E9] mb-2">
              How It Works
            </p>
            <h2 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight">
              From curiosity to a genuine conversation in four steps.
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                num: '01.',
                title: 'Create your profile',
                desc: 'Choose your role, highlight your skills and interests, and set conversation preferences.',
              },
              {
                num: '02.',
                title: 'Discover people',
                desc: 'Select spontaneous matching or align around specific fields, topics, and languages.',
              },
              {
                num: '03.',
                title: 'Start conversations',
                desc: 'Review a concise match card together—both participants accept before text chat begins.',
              },
              {
                num: '04.',
                title: 'Build meaningful connections',
                desc: 'Send a connection request after a great talk to keep learning and collaborating.',
              },
            ].map((item) => (
              <Card key={item.num}>
                <span className="font-mono text-xs text-[#7667F7]">{item.num}</span>
                <h3 className="text-base font-semibold mt-3 mb-2">{item.title}</h3>
                <p className="text-sm text-[#9299AC] leading-relaxed">{item.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* 2. Ways to Connect (Asymmetric Layout) */}
      <section id="ways-to-connect" className="py-20 border-t border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="max-w-2xl mb-12">
            <p className="text-xs font-medium tracking-wide text-[#7667F7] mb-2">
              Ways to Connect
            </p>
            <h2 className="font-display text-2xl sm:text-3xl font-semibold tracking-tight">
              Three intentional paths into a great conversation.
            </h2>
          </div>

          <div className="grid lg:grid-cols-12 gap-6">
            <Card className="lg:col-span-6 flex flex-col justify-between bg-gradient-to-br from-[#171B29] to-[#121625]">
              <div>
                <div className="h-10 w-10 rounded-xl bg-[#7667F7]/15 border border-[#7667F7]/30 flex items-center justify-center mb-5">
                  <Zap className="h-5 w-5 text-[#7667F7]" />
                </div>
                <h3 className="text-xl font-semibold mb-2.5">Meet Someone New</h3>
                <p className="text-sm text-[#9299AC] leading-relaxed max-w-md">
                  Step outside your immediate circle with spontaneous 1-on-1 matching.
                  Filter lightly by students, professionals, or anyone available right now.
                </p>
              </div>
              <div className="pt-6 mt-6 border-t border-white/[0.06] flex items-center justify-between text-xs text-[#9299AC]">
                <span>Spontaneous discovery</span>
                <button
                  type="button"
                  onClick={onStartConnecting}
                  className="text-[#F5F6FA] hover:text-[#36B9E9] font-medium inline-flex items-center gap-1 cursor-pointer"
                >
                  Try Random Connect <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </Card>

            <div className="lg:col-span-6 grid sm:grid-cols-2 lg:grid-cols-1 gap-6">
              <Card>
                <div className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-xl bg-[#36B9E9]/15 border border-[#36B9E9]/30 flex items-center justify-center shrink-0">
                    <Compass className="h-5 w-5 text-[#36B9E9]" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold mb-1.5">Find People Like Me</h3>
                    <p className="text-sm text-[#9299AC] leading-relaxed">
                      Match around specific technologies, design craft, startups, or personal
                      growth topics with peers who share your curiosity.
                    </p>
                  </div>
                </div>
              </Card>

              <Card>
                <div className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-xl bg-[#30C48D]/15 border border-[#30C48D]/30 flex items-center justify-center shrink-0">
                    <Users className="h-5 w-5 text-[#30C48D]" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold mb-1.5">
                      Connect With Professionals
                    </h3>
                    <p className="text-sm text-[#9299AC] leading-relaxed">
                      Have candid conversations with experienced engineers, founders, and
                      mentors—without cold-outreach friction.
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Platform Benefits & 4. Safety and Privacy */}
      <section
        id="safety"
        className="py-20 border-t border-white/[0.06] bg-[#111522]/45"
      >
        <div className="max-w-6xl mx-auto px-4 sm:px-6 grid lg:grid-cols-2 gap-12">
          <div>
            <p className="text-xs font-medium tracking-wide text-[#36B9E9] mb-2">
              Platform Benefits
            </p>
            <h2 className="font-display text-2xl font-semibold mb-6">
              Built for thoughtful dialogue, not passive scrolling.
            </h2>
            <div className="divide-y divide-white/[0.07] border-y border-white/[0.07]">
              {[
                {
                  title: 'Discover new perspectives',
                  desc: 'Meet thoughtful thinkers across universities, industries, and time zones.',
                },
                {
                  title: 'Exchange knowledge',
                  desc: 'Trade real lessons on engineering, design, research, and early-stage ventures.',
                },
                {
                  title: 'Build professional relationships',
                  desc: 'Connect organically through conversation before requesting to stay in touch.',
                },
                {
                  title: 'Explore opportunities',
                  desc: 'Uncover mentorship, collaborations, and fresh career directions naturally.',
                },
              ].map((b) => (
                <div key={b.title} className="py-4">
                  <h3 className="text-sm font-semibold text-[#F5F6FA]">{b.title}</h3>
                  <p className="text-sm text-[#9299AC] mt-1">{b.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-medium tracking-wide text-[#30C48D] mb-2">
              Safety and Privacy
            </p>
            <h2 className="font-display text-2xl font-semibold mb-6">
              Trust and user control in every interaction.
            </h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                {
                  icon: <UserCheck className="h-4 w-4 text-[#30C48D]" />,
                  title: 'Verified profiles',
                  desc: '18+ onboarding and structured categories keep participation accountable.',
                },
                {
                  icon: <ShieldCheck className="h-4 w-4 text-[#7667F7]" />,
                  title: 'User-controlled connections',
                  desc: 'Both users accept before chat opens, and connections require mutual approval.',
                },
                {
                  icon: <Lock className="h-4 w-4 text-[#36B9E9]" />,
                  title: 'Privacy protection',
                  desc: 'Email and private settings remain hidden from other members at all times.',
                },
                {
                  icon: <MessageSquare className="h-4 w-4 text-[#F16C79]" />,
                  title: 'Reporting and blocking',
                  desc: 'Immediate end, block, and moderation reporting directly from every chat.',
                },
              ].map((s) => (
                <Card key={s.title} className="p-5">
                  <div className="mb-3">{s.icon}</div>
                  <h3 className="text-sm font-semibold">{s.title}</h3>
                  <p className="text-xs text-[#9299AC] mt-1.5 leading-relaxed">
                    {s.desc}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 5. Final CTA & Footer */}
      <section className="py-20 border-t border-white/[0.06]">
        <div className="max-w-3xl mx-auto px-4 text-center space-y-5">
          <h2 className="font-display text-3xl font-semibold tracking-tight">
            Find someone worth talking to today.
          </h2>
          <p className="text-sm sm:text-base text-[#9299AC] max-w-xl mx-auto">
            Create your profile and start a focused 1-on-1 conversation with students,
            professionals, entrepreneurs, or mentors.
          </p>
          <div className="pt-2">
            <Button size="lg" onClick={onStartConnecting}>
              Start Connecting
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/[0.06] py-8 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#9299AC]">
          <p>© {new Date().getFullYear()} Valence. Real-time text-first human connection.</p>
          <div className="flex items-center gap-6">
            <button
              type="button"
              onClick={onOpenAdminPreview}
              className="hover:text-[#F5F6FA] transition-colors cursor-pointer"
            >
              Admin Console
            </button>
            <button
              type="button"
              onClick={onLogin}
              className="hover:text-[#F5F6FA] transition-colors cursor-pointer"
            >
              Member Sign In
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};
