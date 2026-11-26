# Studable — Privacy Policy

**Effective Date:** November 26, 2026  
**Last Updated:** November 26, 2026

Welcome to Studable ("we", "our", or "us"). We are committed to protecting your privacy and ensuring you have a safe and constructive networking experience. This Privacy Policy explains how we collect, use, store, and protect your information when you access or use the Studable application, website, and related real-time networking services.

---

## 1. Age Eligibility & COPPA Compliance

Studable is intended strictly for individuals aged **13 years or older**. In accordance with the Children’s Online Privacy Protection Act (COPPA) and international child privacy regulations:
- We do not knowingly collect, solicit, or maintain personal information from anyone under the age of 13.
- During registration, age verification is enforced. Any registration indicating an age under 13 is automatically rejected.
- If we become aware that an account belongs to a user under the age of 13, that account and all associated personal data will be deleted immediately.

---

## 2. Information We Collect

### A. Information You Provide Directly
- **Account Registration:** Username, display name, email address, password (stored using one-way Argon2 password hashing), and verified age.
- **Profile Information:** Category (Student, Working Professional, Entrepreneur, Mentor), headline, biography, avatar URL, and skills.
- **Matching Preferences:** Academic and career interests, preferred languages, and connection audience preferences (Students, Professionals, Anyone).
- **Communication & Interactions:** Messages sent in 1-on-1 conversations, report descriptions, and feedback.

### B. Information Collected Automatically
- **Real-Time Presence:** Online, available, matching, in-conversation, and offline states.
- **Session Data:** IP address, browser type, device information, and active session tickets.
- **Security Logs:** Authentication attempts, password change timestamps, and rate limiting events.

---

## 3. How We Use Your Information

We process your data for the following essential purposes:
1. **Real-Time Matching:** Pairing you with peers based on shared interests, language compatibility, and waiting duration.
2. **Direct Messaging:** Delivering real-time chat messages, message delivery confirmations, and read receipts.
3. **Safety & Moderation:** Investigating abuse reports, filtering spam, enforcing blocks, and executing administrative suspensions.
4. **Account Maintenance:** Sending transactional emails (email verification and password resets). We do not send marketing spam.

---

## 4. Privacy Controls & User Preferences

You maintain direct control over your visibility and matching preferences through your Profile and Privacy Settings:
- **Online Presence Visibility (`show_online_status`):** When toggled off, your presence displays as `OFFLINE` to other members, and you are excluded from the public lobby directory.
- **Random Discovery (`allow_random_discovery`):** When disabled, your profile is excluded from the random matching engine.
- **Audience Filtering:** You can restrict discovery to students, professionals, or anyone.
- **Blocking:** You can block any member at any time. Blocking immediately terminates messaging capability between both parties.

---

## 5. Data Retention & Deletion

- **Account Deletion:** You can delete your account at any time via Settings (`DELETE /api/v1/users/me`).
- **Soft Deletion & Moderation:** Upon account deletion, personal credentials are deleted, profile records are soft-deleted (`deleted_at`), and active sessions are revoked immediately. Conversation participants are disassociated (`SET NULL`) so transcripts remain intact for unresolved safety and moderation audits.
- **Stale Session Cleanup:** Ephemeral presence sessions automatically expire via Redis TTL leases when disconnected.

---

## 6. Information Security

We implement industry-standard technical and organizational security controls:
- **Passwords:** Hashed using **Argon2id** with salt. Passwords are never logged or stored in plain text.
- **Authentication:** Stateless short-lived JWT access tokens (15-minute expiration) paired with securely stored refresh tokens that can be revoked globally.
- **Encryption:** All transit communications are protected by TLS/HTTPS and Secure WebSockets (WSS).
- **Session Revocation:** Triggering password change, password reset, or admin suspension immediately revokes all active refresh tokens and presence connections across all devices.

---

## 7. Contact Us

For privacy inquiries, data access requests, or to exercise your GDPR/CCPA rights, please contact our Data Protection Team at:
- **Email:** `privacy@studable.app`
