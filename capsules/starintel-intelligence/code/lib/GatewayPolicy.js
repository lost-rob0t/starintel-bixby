const SAFE_ERROR_CODES = new Set([
  'UNAUTHORIZED',
  'FORBIDDEN',
  'INVALID_REQUEST',
  'PERSON_NOT_FOUND',
  'AMBIGUOUS_PERSON',
  'DOCUMENTS_NOT_FOUND',
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

function hostFromOrigin(origin) {
  const match = /^https:\/\/([^/?#]+)\/?$/i.exec(origin)
  if (!match) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
  }

  const authority = match[1]
  if (authority.includes('@')) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
  }

  if (authority.startsWith('[')) {
    const end = authority.indexOf(']')
    if (end === -1) {
      throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
    }
    const remainder = authority.slice(end + 1)
    if (remainder && !/^:\d+$/.test(remainder)) {
      throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
    }
    return authority.slice(1, end).toLowerCase()
  }

  const parts = authority.split(':')
  if (parts.length > 2 || (parts.length === 2 && !/^\d+$/.test(parts[1]))) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is invalid.')
  }
  return parts[0].replace(/\.$/, '').toLowerCase()
}

function isPrivateIpv4(host) {
  const octets = host.split('.')
  if (octets.length !== 4 || octets.some(part => !/^\d{1,3}$/.test(part))) {
    return false
  }
  const values = octets.map(Number)
  if (values.some(value => value < 0 || value > 255)) {
    return true
  }
  const [a, b] = values
  return (
    a === 0 ||
    a === 10 ||
    a === 127 ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    a >= 224
  )
}

function isPrivateHost(host) {
  if (!host) return true
  if (host === 'localhost' || host.endsWith('.localhost')) return true
  if (host === 'star.intel' || host.endsWith('.star.intel')) return true
  if (isPrivateIpv4(host)) return true

  const ipv6 = host.toLowerCase()
  return (
    ipv6 === '::1' ||
    ipv6 === '::' ||
    ipv6.startsWith('fc') ||
    ipv6.startsWith('fd') ||
    ipv6.startsWith('fe8') ||
    ipv6.startsWith('fe9') ||
    ipv6.startsWith('fea') ||
    ipv6.startsWith('feb')
  )
}

export function validateGatewayOrigin(value) {
  if (typeof value !== 'string' || !value.trim() || value !== value.trim()) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin is not configured.')
  }
  const host = hostFromOrigin(value)
  if (isPrivateHost(host)) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway origin must be public HTTPS.')
  }
  return value.endsWith('/') ? value.slice(0, -1) : value
}

export function boundedDocumentLimit(value) {
  if (value === undefined || value === null || value === '') return 5
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return 5
  return Math.max(1, Math.min(10, Math.trunc(parsed)))
}

function optionalText(value) {
  if (value === undefined || value === null) return undefined
  const text = String(value).trim()
  return text || undefined
}

export function buildPersonResolveRequest(query) {
  const cleanQuery = optionalText(query)
  if (!cleanQuery) {
    throw new GatewayError('INVALID_REQUEST', 'A person query is required.')
  }
  return { query: cleanQuery }
}

export function buildDocumentSearchRequest(input = {}) {
  const query = optionalText(input.query)
  const personId = optionalText(input.personId)
  const dtype = optionalText(input.dtype)
  if (!query && !personId) {
    throw new GatewayError('INVALID_REQUEST', 'A document query or selected person is required.')
  }

  const request = {}
  if (query) request.query = query
  if (personId) request.personId = personId
  if (dtype) request.dtype = dtype
  request.limit = boundedDocumentLimit(input.limit)
  return request
}

function safeErrorCode(status, parsed) {
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
    case 'UNAUTHORIZED': return 'StarIntel authorization is required.'
    case 'FORBIDDEN': return 'This StarIntel action is not permitted.'
    case 'INVALID_REQUEST': return 'The StarIntel request is invalid.'
    case 'PERSON_NOT_FOUND': return 'That person was not found.'
    case 'AMBIGUOUS_PERSON': return 'More than one person matched.'
    case 'DOCUMENTS_NOT_FOUND': return 'No matching documents were found.'
    case 'RATE_LIMITED': return 'StarIntel is receiving too many requests.'
    case 'UPSTREAM_TIMEOUT': return 'StarIntel did not respond in time.'
    case 'UPSTREAM_UNAVAILABLE': return 'StarIntel is temporarily unavailable.'
    default: return 'StarIntel could not complete the request.'
  }
}

function validatePath(path) {
  if (typeof path !== 'string' || !/^\/v1\/bixby\/[A-Za-z0-9/_-]+$/.test(path) || path.includes('..')) {
    throw new GatewayError('INVALID_REQUEST', 'The StarIntel gateway path is invalid.')
  }
  return path
}

export function postJson(httpClient, origin, path, body) {
  const base = validateGatewayOrigin(origin)
  const safePath = validatePath(path)
  let response
  try {
    response = httpClient.postUrl(`${base}${safePath}`, body, {
      format: 'json',
      passAsJson: true,
      returnHeaders: true,
    })
  } catch (_error) {
    throw new GatewayError('UPSTREAM_UNAVAILABLE', safeMessage('UPSTREAM_UNAVAILABLE'))
  }

  const status = Number(response && response.status)
  const parsed = response && response.parsed
  if (status >= 200 && status < 300) {
    return parsed
  }

  const code = safeErrorCode(status, parsed)
  throw new GatewayError(code, safeMessage(code))
}

export default {
  GatewayError,
  boundedDocumentLimit,
  buildDocumentSearchRequest,
  buildPersonResolveRequest,
  postJson,
  validateGatewayOrigin,
}
