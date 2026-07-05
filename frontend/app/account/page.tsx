'use client'

import { motion } from 'framer-motion'
import { AccountDataExport } from '@/components/AccountDataExport'
import { AccountDeletion } from '@/components/AccountDeletion'
import { ApiKeySettings } from '@/components/ApiKeySettings'
import { BrandMark } from '@/components/BrandMark'
import { spring } from '@/lib/motion'

// Account & security — separated from /profile (career content that feeds
// generation). This page is administrative: billing key, data export, and
// account deletion. Session/device management lives natively in Clerk's own
// "Manage account" modal (the UserButton in the navbar) rather than being
// duplicated here — Clerk's UserProfile component already lists active
// sessions and lets you revoke them individually.
export default function AccountPage() {
  return (
    <div className="px-6 pb-24 max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="pt-10 mb-10"
      >
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ ...spring.bouncy, delay: 0.04 }}
          className="brand-ring-glow-cool mb-4 text-neutral-900"
        >
          <BrandMark size={28} physicalStroke={1.5} />
        </motion.div>
        <h1 className="text-3xl font-semibold text-neutral-900">Settings</h1>
        <p className="text-sm text-neutral-600 mt-1">
          Billing key, data export, and account deletion. Career content lives separately, under Resume.
        </p>
      </motion.div>

      {/* API key — required before anything else works */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.02 }}
        className="mb-10"
      >
        <ApiKeySettings />
      </motion.section>

      {/* Account data export — rare, deliberate action */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.04 }}
        className="mb-10 pt-10"
        style={{ borderTop: '1px solid var(--c-border)' }}
      >
        <AccountDataExport />
      </motion.section>

      {/* Danger zone — deliberately last, visually separated from everyday actions */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...spring.gentle, delay: 0.06 }}
        className="pt-10"
        style={{ borderTop: '1px solid var(--c-border)' }}
      >
        <AccountDeletion />
      </motion.section>
    </div>
  )
}
