import {
  AppNotification,
  ChatMessage,
  ConnectionRecord,
  ModerationReport,
  OwnAccountSettings,
  UserProfile,
} from '../types/domain';

export const HERO_ILLUSTRATION_URL = '/src/assets/images/hero_connection_network_1794910717453.jpg';

export const PROTOTYPE_CURRENT_USER: UserProfile = {
  id: 'usr_self',
  displayName: 'Aarav Mehta',
  category: 'Working Professional',
  headline: 'Product Engineer · Distributed Systems',
  bio: 'Building developer tooling and exploring AI-assisted workflows. Always glad to trade notes with students, builders, and designers.',
  skills: ['TypeScript', 'Python', 'FastAPI', 'System Design'],
  interests: ['Technology', 'AI and Machine Learning', 'Startups', 'Design'],
  languages: ['English', 'Hindi'],
  connectionCount: 18,
  isVerified: true,
};

export const PROTOTYPE_SETTINGS: OwnAccountSettings = {
  email: 'aarav.mehta@example.com',
  preferredAudience: 'Anyone',
  preferredLanguage: 'English',
  preferredTopics: ['Early-stage product architecture', 'Breaking into AI engineering'],
  defaultMatchingMode: 'interest',
  allowRandomDiscovery: true,
  showOnlineStatus: true,
  notifyConnectionRequests: true,
  notifyMessages: true,
};

export const PROTOTYPE_PEERS: UserProfile[] = [
  {
    id: 'usr_elena',
    displayName: 'Elena Vance',
    avatarUrl: '/src/assets/images/avatar_elena_1794910718585.jpg',
    category: 'Mentor',
    headline: 'Staff Design Technologist · Former Founder',
    bio: 'Ten years helping engineers transition into product leadership and design systems architecture. Happy to review portfolios or chat product strategy.',
    skills: ['Product Strategy', 'Design Systems', 'Mentorship', 'UI Architecture'],
    interests: ['Design', 'Career Development', 'Entrepreneurship', 'Technology'],
    languages: ['English', 'Spanish'],
    connectionCount: 64,
    isVerified: true,
  },
  {
    id: 'usr_rohan',
    displayName: 'Rohan Kapoor',
    avatarUrl: '/src/assets/images/avatar_rohan_1794910718800.jpg',
    category: 'Student',
    headline: 'M.S. Computer Science · Applied ML Researcher',
    bio: 'Researching small language models and inference optimization. Looking to learn about real-world production tradeoffs from industry practitioners.',
    skills: ['PyTorch', 'Rust', 'CUDA', 'Evaluation'],
    interests: ['AI and Machine Learning', 'Programming', 'Education'],
    languages: ['English', 'Hindi'],
    connectionCount: 12,
    isVerified: true,
  },
  {
    id: 'usr_claire',
    displayName: 'Claire Lin',
    avatarUrl: '/src/assets/images/avatar_claire_1794910718917.jpg',
    category: 'Entrepreneur',
    headline: 'Co-founder · Climate Data Analytics',
    bio: 'Bootstrapping B2B sustainability tools. Always up for candid conversations on customer discovery, pricing experiments, and resilient early teams.',
    skills: ['Go-to-Market', 'Data Analytics', 'Customer Discovery'],
    interests: ['Startups', 'Business', 'Entrepreneurship'],
    languages: ['English', 'Mandarin'],
    connectionCount: 41,
    isVerified: true,
  },
];

export const PROTOTYPE_CONNECTIONS: ConnectionRecord[] = [
  {
    id: 'conn_1',
    user: PROTOTYPE_PEERS[0],
    status: 'accepted',
    connectedAt: '2 days ago',
    sharedTopic: 'Design systems at scale',
  },
  {
    id: 'conn_2',
    user: PROTOTYPE_PEERS[1],
    status: 'pending_incoming',
    sharedTopic: 'Applied ML career paths',
  },
  {
    id: 'conn_3',
    user: PROTOTYPE_PEERS[2],
    status: 'pending_outgoing',
    sharedTopic: 'B2B customer discovery',
  },
];

export const PROTOTYPE_MESSAGES_BY_PEER: Record<string, ChatMessage[]> = {
  usr_elena: [
    {
      id: 'msg_1',
      conversationId: 'conv_elena',
      senderId: 'usr_elena',
      content: 'Hi Aarav! Glad we matched on product architecture. What kind of tooling are you exploring lately?',
      createdAt: '10:14 AM',
      status: 'delivered',
    },
    {
      id: 'msg_2',
      conversationId: 'conv_elena',
      senderId: 'usr_self',
      content: 'Hey Elena! Mostly real-time collaborative interfaces and keeping state transitions predictable across clients.',
      createdAt: '10:15 AM',
      status: 'delivered',
    },
  ],
  usr_rohan: [
    {
      id: 'msg_3',
      conversationId: 'conv_rohan',
      senderId: 'usr_rohan',
      content: 'Hey! Curious how you evaluate whether an ML feature needs a custom backend pipeline vs a lightweight API call.',
      createdAt: '11:02 AM',
      status: 'delivered',
    },
  ],
};

export const PROTOTYPE_NOTIFICATIONS: AppNotification[] = [
  {
    id: 'notif_1',
    type: 'connection_request',
    title: 'New connection request',
    description: 'Rohan Kapoor would like to connect after your recent topic match.',
    timestamp: '14m ago',
    read: false,
    relatedUserId: 'usr_rohan',
  },
  {
    id: 'notif_2',
    type: 'connection_accepted',
    title: 'Connection accepted',
    description: 'Elena Vance accepted your connection request.',
    timestamp: '2d ago',
    read: true,
    relatedUserId: 'usr_elena',
  },
  {
    id: 'notif_3',
    type: 'new_message',
    title: 'New message from Elena Vance',
    description: 'Sent a note in Design systems at scale.',
    timestamp: '2d ago',
    read: true,
    relatedUserId: 'usr_elena',
  },
  {
    id: 'notif_4',
    type: 'account_update',
    title: 'Profile preferences saved',
    description: 'Your matching defaults are set to Interest-Based Discovery in English.',
    timestamp: '4d ago',
    read: true,
  },
  {
    id: 'notif_5',
    type: 'moderation',
    title: 'Community safety verification active',
    description: 'Your 18+ member verification is active. Thank you for keeping conversations constructive.',
    timestamp: '5d ago',
    read: true,
  },
];

export const PROTOTYPE_REPORTS: ModerationReport[] = [
  {
    id: 'rep_901',
    reportedUserId: 'usr_884',
    reportedUserName: 'Marcus K.',
    reporterId: 'usr_221',
    reason: 'Unsolicited promotional links',
    details: 'Repeatedly pasted external affiliate links immediately after match start.',
    status: 'pending',
    createdAt: '18 mins ago',
  },
  {
    id: 'rep_902',
    reportedUserId: 'usr_712',
    reportedUserName: 'Devon S.',
    reporterId: 'usr_318',
    reason: 'Off-topic harassment',
    details: 'Sent dismissive messages after the other participant declined to share personal social links.',
    status: 'pending',
    createdAt: '2 hours ago',
  },
  {
    id: 'rep_900',
    reportedUserId: 'usr_519',
    reportedUserName: 'Dev P.',
    reporterId: 'usr_109',
    reason: 'Disrespectful conduct',
    details: 'Used hostile language when declining a topic.',
    status: 'resolved_warned',
    createdAt: 'Yesterday',
  },
];

export const POPULAR_TOPICS = [
  'Transitioning into AI Engineering',
  'First-time Founder Mistakes',
  'Portfolio & Design Reviews',
  'Remote Engineering Culture',
  'Balancing Research & Industry',
];
