const SAFE_ERROR_CODES = new Set([
  'UNAUTHORIZED',
  'FORBIDDEN',
  'INVALID_REQUEST',
  'TARGET_TYPE_UNSUPPORTED',
  'ACTOR_UNSUPPORTED',
  'AUTODIG_CAPABILITY_UNAVAILABLE',
  'AUTODIG_RUN_NOT_FOUND',
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

function internalError() {
  return new GatewayError('INTERNAL_ERROR', 'StarIntel returned an invalid response.')
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

function requiredOutputText(value) {
  const text = optionalText(value)
  if (!text) throw internalError()
  return text
}

function isPrivateIpv4(host) {
  const octets = host.split('.')
  if (octets.length !== 4 || octets.some(part => !/^\d{1,3}$/.test(part))) return false
  const values = octets.map(Number)
  if (values.some(value => value < 0 || value > 255)) return true
  const [a, b] = values
  return a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224
}

export function validateGatewayOrigin(origin) {
  if (typeof origin !== 'string' || !origin.trim() || origin !== origin.trim()) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
  }
  const match = /^https:\/\/([A-Za-z0-9.-]+)(?::\d+)?\/?$/.exec(origin)
  if (!match) throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
  const host = match[1].replace(/\.$/, '').toLowerCase()
  if (host === 'localhost' || host.endsWith('.localhost') || host === 'star.intel' ||
      host.endsWith('.star.intel') || isPrivateIpv4(host)) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin must be public HTTPS.')
  }
  return origin.endsWith('/') ? origin.slice(0, -1) : origin
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
    case 'INVALID_REQUEST': return 'The StarIntel request is invalid.'
    case 'TARGET_TYPE_UNSUPPORTED': return 'That target type is not supported.'
    case 'ACTOR_UNSUPPORTED': return 'That target actor is not supported.'
    case 'AUTODIG_CAPABILITY_UNAVAILABLE': return 'Auto-Dig control is not available right now.'
    case 'AUTODIG_RUN_NOT_FOUND': return 'That Auto-Dig run could not be found.'
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
  const base = validateGatewayOrigin(origin)
  if (!/^\/v1\/bixby\/(?:targets\/(?:prepare|commit)|autodig\/(?:status|run|runs|start|pause|resume|stop))$/.test(path)) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway path is invalid.')
  }
  try {
    return parse(httpClient.oauthPostUrl(`${base}${path}`, body, {
      format: 'json', passAsJson: true, returnHeaders: true,
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

export function buildRunRequest(runId) {
  return { runId: requiredText(runId, 'An Auto-Dig run is required.') }
}

export function buildStartRequest(target) {
  return { target: requiredText(target, 'An Auto-Dig target is required.') }
}

export function normalizeAutoDigRun(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = {
    runId: requiredOutputText(value.runId),
    status: requiredOutputText(value.status),
  }
  const requestId = optionalText(value.requestId)
  const target = optionalText(value.target)
  if (requestId) result.requestId = requestId
  if (target) result.target = target
  return result
}

export function normalizeAutoDigRunList(value) {
  const runs = Array.isArray(value) ? value : (value && Array.isArray(value.runs) ? value.runs : null)
  if (!runs) throw internalError()
  return { runs: runs.slice(0, 20).map(normalizeAutoDigRun) }
}

export function normalizeTargetDraft(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = { draftId: requiredOutputText(value.draftId), subject: requiredOutputText(value.subject) }
  const targetType = optionalText(value.targetType)
  const actor = optionalText(value.actor)
  if (targetType) result.targetType = targetType
  if (actor) result.actor = actor
  return result
}

export function normalizeTargetReceipt(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  return { receiptId: requiredOutputText(value.receiptId), status: requiredOutputText(value.status) }
}

export default {
  GatewayError,
  buildCommitRequest,
  buildPrepareRequest,
  buildRunRequest,
  buildStartRequest,
  normalizeAutoDigRun,
  normalizeAutoDigRunList,
  normalizeTargetDraft,
  normalizeTargetReceipt,
  postAuthorized,
  validateGatewayOrigin,
}
