'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion } from 'framer-motion'

const links = [
  { href: '/', label: 'Home' },
  { href: '/applications', label: 'Applications' },
  { href: '/profile', label: 'Profile' },
]

export function Navbar() {
  const pathname = usePathname()

  return (
    <motion.div
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-48px)] max-w-4xl"
    >
      <div
        style={{
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          background: 'rgba(250, 250, 248, 0.85)',
          border: '1px solid rgba(255,255,255,0.6)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        }}
        className="rounded-2xl px-5 py-3 flex items-center justify-between"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div
            style={{ background: 'linear-gradient(135deg, #818cf8, #a78bfa)' }}
            className="w-7 h-7 rounded-lg flex items-center justify-center"
          >
            <span className="text-white text-xs font-bold">C</span>
          </div>
          <span className="text-sm font-semibold text-neutral-800 tracking-tight">CareerOS</span>
        </Link>

        {/* Links */}
        <nav className="flex items-center gap-1">
          {links.map(({ href, label }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={`px-4 py-1.5 rounded-xl text-sm transition-all duration-200 ${
                  active
                    ? 'bg-white text-neutral-900 font-medium shadow-sm shadow-black/5'
                    : 'text-neutral-500 hover:text-neutral-800 hover:bg-white/60'
                }`}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Avatar */}
        <div
          style={{ background: 'linear-gradient(135deg, #818cf8, #a78bfa)' }}
          className="w-8 h-8 rounded-full flex items-center justify-center"
        >
          <span className="text-white text-xs font-semibold">K</span>
        </div>
      </div>
    </motion.div>
  )
}
