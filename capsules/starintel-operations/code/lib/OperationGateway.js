const SAFE_ERROR_CODES = new Set([
  'UNAUTHORIZED',
  'FORBIDDEN',
  'INVALID_REQUEST',
  'TARGET_TYPE_UNSUPPORTED',
  'ACTOR_UNSUPPORTED',
  'RATE_LIMITED',
  'UPSTREAM_TIMEOUT',
  'UPSTREAM_UNAVAILABLE',
  'INTERNAL_ERROR',
])

export class GatewayError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'GatewayError'
    this.code = code
  }
}

function optionalText(value) {
  if (value === undefined || value === null) return undefined
  const text = String(value).trim()
  return text || undefined
}

function requiredText(value, message) {
  const text = optionalText(value)
  if (!text) throw new GatewayError('INVALID_REQUEST', message)
  return text
}

function validateOrigin(origin) {
  if (typeof origin !== 'string' || !/^https:\/\/[A-Za-z0-9.-]+(?::\d+)?$/.test(origin)) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
  }
  const host = origin.replace(/^https:\/\//, '').split(':')[0].toLowerCase()
  if (host === 'localhost' || host.endsWith('.localhost') || host === 'star.intel' || host.endsWith('.star.intel')) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin must be public HTTPS.')
  }
  return origin
}

function safeCode(status, parsed) {
  const upstream = parsed && typeof parsed === 'object'
    ? (parsed.error && typeof parsed.error === 'object' ? parsed.error.code : parsed.code)
    : undefined
  if (SAFE_ERROR_CODES.has(upstream)) return upstream
  if (status === 401) return 'UNAUTHORIZED'
  if (status === 403) return 'FORBIDDEN'
  if (status === 429) return 'RATE_LIMITED'
  if (status === 408 || status === 504) return 'UPSTREAM_TIMEOUT'
  if (status === 502 || status === 503) return 'UPSTREAM_UNAVAILABLE'
  return 'INTERNAL_ERROR'
}

function safeMessage(code) {
  switch (code) {
    case 'UNAUTHORIZED': return 'Please reconnect your StarIntel account.'
    case 'FORBIDDEN': return 'This StarIntel action is not permitted.'
    case 'INVALID_REQUEST': return 'The target request is invalid.'
    case 'TARGET_TYPE_UNSUPPORTED': return 'That target type is not supported.'
    case 'ACTOR_UNSUPPORTED': return 'That target actor is not supported.'
    case 'RATE_LIMITED': return 'StarIntel is receiving too many requests.'
    case 'UPSTREAM_TIMEOUT': return 'StarIntel did not respond in time.'
    case 'UPSTREAM_UNAVAILABLE': return 'StarIntel is temporarily unavailable.'
    default: return 'StarIntel could not complete the request.'
  }
}

function parse(response) {
  const status = Number(response && response.status)
  if (status >= 200 && status < 300) return response.parsed
  const code = safeCode(status, response && response.parsed)
  if (status === 401) {
    const error = new Error('StarIntel authorization must be refreshed.')
    error.$type = 'authorization-error'
    error.$message = safeMessage('UNAUTHORIZED')
    throw error
  }
  throw new GatewayError(code, safeMessage(code))
}

export function postAuthorized(httpClient, origin, path, body) {
  const base = validateOrigin(origin)
  if (!/^\/v1\/bixby\/targets\/(?:prepare|commit)$/.test(path)) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway path is invalid.')
  }
  try {
    return parse(httpClient.oauthPostUrl(`${base}${path}`, body, {
      format: 'json',
      passAsJson: true,
      returnHeaders: true,
    }))
  } catch (error) {
    if (error && error.$type === 'authorization-error') throw error
    if (error instanceof GatewayError) throw error
    throw new GatewayError('UPSTREAM_UNAVAILABLE', safeMessage('UPSTREAM_UNAVAILABLE'))
  }
}

export function buildPrepareRequest(input = {}) {
  const request = { subject: requiredText(input.subject, 'A target subject is required.') }
  const targetType = optionalText(input.targetType)
  const actor = optionalText(input.actor)
  if (targetType) request.targetType = targetType
  if (actor) request.actor = actor
  return request
}

export function buildCommitRequest(draft) {
  if (!draft || typeof draft !== 'object' || Array.isArray(draft)) {
    throw new GatewayError('INVALID_REQUEST', 'A prepared target draft is required.')
  }
  return { draftId: requiredText(draft.draftId, 'A prepared target draft is required.') }
}

export default {
  GatewayError,
  buildCommitRequest,
  buildPrepareRequest,
  postAuthorized,
}
