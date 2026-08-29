type JobFailureMetadata = Record<string, unknown> | null | undefined

export function generationFailureMessage(metadata: JobFailureMetadata): string {
  const code = typeof metadata?.failure_code === 'string' ? metadata.failure_code : 'generation_failed'

  switch (code) {
    case 'anthropic_timeout':
      return 'Claude took too long to respond. Try again.'
    case 'api_key_invalid':
      return 'Your Anthropic API key was rejected. Update it in Settings and try again.'
    case 'anthropic_rate_limit':
      return 'Claude is temporarily rate-limited. Wait a moment and try again.'
    case 'anthropic_unavailable':
      return 'Claude is temporarily unavailable. Try again shortly.'
    case 'generation_interrupted':
      return 'Generation was interrupted before it finished. Retry when you’re ready.'
    case 'generation_configuration':
      return 'Generation hit a configuration error. The app needs an update before retrying.'
    default:
      return 'Generation failed unexpectedly. Try again.'
  }
}
