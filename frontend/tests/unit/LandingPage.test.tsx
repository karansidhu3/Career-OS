import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { LandingPage } from '@/components/LandingPage'
import { api } from '@/lib/api'

vi.mock('@/lib/api', () => ({
  api: { joinWaitlist: vi.fn() },
}))

describe('LandingPage', () => {
  beforeEach(() => {
    vi.mocked(api.joinWaitlist).mockReset()
  })

  it('renders the BYO-key trust message', () => {
    render(<LandingPage />)
    expect(screen.getByText(/you bring your own ai key/i)).toBeInTheDocument()
    expect(screen.getByText(/never sees or pays for your usage/i)).toBeInTheDocument()
  })

  it('renders an email input and a sign-in link for already-invited users', () => {
    render(<LandingPage />)
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/sign-in')
  })

  it('submits the entered email and shows the joined state on success', async () => {
    vi.mocked(api.joinWaitlist).mockResolvedValue({ status: 'joined' })
    render(<LandingPage />)

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'friend@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /join the waitlist/i }))

    await waitFor(() => expect(screen.getByText(/you.re on the list/i)).toBeInTheDocument())
    expect(api.joinWaitlist).toHaveBeenCalledWith('friend@example.com')
  })

  it('shows an error message and stays on the form if the request fails', async () => {
    vi.mocked(api.joinWaitlist).mockRejectedValue(new Error('network error'))
    render(<LandingPage />)

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'friend@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /join the waitlist/i }))

    await waitFor(() => expect(screen.getByText(/couldn.t join the waitlist/i)).toBeInTheDocument())
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
  })

  it('disables the submit button while the request is in flight', async () => {
    let resolveFn: (v: { status: string }) => void
    vi.mocked(api.joinWaitlist).mockReturnValue(new Promise(resolve => { resolveFn = resolve }))
    render(<LandingPage />)

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'friend@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /join the waitlist/i }))

    expect(await screen.findByRole('button', { name: /joining/i })).toBeDisabled()
    await act(async () => { resolveFn!({ status: 'joined' }) })
  })
})
