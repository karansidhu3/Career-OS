import '@testing-library/jest-dom'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResumePreview } from '@/components/ResultSections'

describe('ResumePreview', () => {
  it('shows a fetched PDF without waiting for the iframe load event', () => {
    render(<ResumePreview jobId={1} blobUrl="blob:resume" failed={false} />)

    expect(screen.queryByText('Compiling PDF…')).not.toBeInTheDocument()
    expect(screen.getByTitle('Resume')).toHaveStyle({ opacity: '1' })
  })
})
