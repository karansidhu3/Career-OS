import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LandingPage } from '@/components/LandingPage'

const push = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}))

describe('LandingPage', () => {
  beforeEach(() => {
    push.mockReset()
  })

  it('renders an email input and a sign-in link for returning users', () => {
    render(<LandingPage />)
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/sign-in')
  })

  it('renders Terms and Privacy links', () => {
    render(<LandingPage />)
    expect(screen.getByRole('link', { name: /terms/i })).toHaveAttribute('href', '/terms')
    expect(screen.getByRole('link', { name: /privacy/i })).toHaveAttribute('href', '/privacy')
  })

  it('routes to sign-up with the entered email on submit, instead of hitting a waitlist API', () => {
    render(<LandingPage />)

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'friend@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /get started/i }))

    expect(push).toHaveBeenCalledWith('/sign-up?email=friend%40example.com')
  })

  it('does not navigate if the email field is empty', () => {
    render(<LandingPage />)

    fireEvent.click(screen.getByRole('button', { name: /get started/i }))

    expect(push).not.toHaveBeenCalled()
  })
})
