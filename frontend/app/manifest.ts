import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'CareerOS',
    short_name: 'CareerOS',
    description: 'Tailored resumes and cover letters, instantly.',
    start_url: '/',
    display: 'standalone',
    background_color: '#111110',
    theme_color: '#111110',
    icons: [
      { src: '/icon-192', sizes: '192x192', type: 'image/png' },
      { src: '/icon-512', sizes: '512x512', type: 'image/png' },
    ],
  }
}
