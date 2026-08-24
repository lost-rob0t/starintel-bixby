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

function internalError() {
  return new GatewayError('INTERNAL_ERROR', 'StarIntel returned an invalid response.')
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

function requiredText(value) {
  const text = optionalText(value)
  if (!text) throw internalError()
  return text
}

function optionalTextArray(value) {
  if (value === undefined || value === null) return undefined
  if (!Array.isArray(value)) throw internalError()
  const items = value.map(optionalText).filter(Boolean)
  return items.length ? items : undefined
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

function normalizePersonMatch(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = {
    id: requiredText(value.id),
    name: requiredText(value.name),
  }
  const aliases = optionalTextArray(value.aliases)
  const knownIdentifiers = optionalTextArray(value.knownIdentifiers)
  if (aliases) result.aliases = aliases
  if (knownIdentifiers) result.knownIdentifiers = knownIdentifiers
  if (value.score !== undefined && value.score !== null) {
    const score = Number(value.score)
    if (!Number.isFinite(score)) throw internalError()
    result.score = score
  }
  return result
}

function normalizePersonProfile(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = {
    id: requiredText(value.id),
    name: requiredText(value.name),
  }
  const aliases = optionalTextArray(value.aliases)
  const knownIdentifiers = optionalTextArray(value.knownIdentifiers)
  const summary = optionalText(value.summary)
  if (aliases) result.aliases = aliases
  if (knownIdentifiers) result.knownIdentifiers = knownIdentifiers
  if (summary) result.summary = summary
  return result
}

export function normalizePersonSearchResult(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = { query: requiredText(value.query) }
  const matches = value.matches === undefined || value.matches === null
    ? []
    : Array.isArray(value.matches)
      ? value.matches.map(normalizePersonMatch)
      : (() => { throw internalError() })()
  if (value.matches !== undefined && value.matches !== null) result.matches = matches

  if (value.profile !== undefined && value.profile !== null) {
    const profile = normalizePersonProfile(value.profile)
    if (matches.length > 1) throw internalError()
    if (matches.length === 1 && matches[0].id !== profile.id) throw internalError()
    result.profile = profile
  }
  return result
}

function validatePublicDocumentUrl(value) {
  const text = requiredText(value)
  if (text !== String(value)) throw internalError()
  const match = /^https:\/\/([^/?#]+)(\/[^?#]*)?(?:[?#].*)?$/i.exec(text)
  if (!match || match[1].includes('@')) throw internalError()
  let host
  try {
    host = hostFromOrigin(`https://${match[1]}`)
  } catch (_error) {
    throw internalError()
  }
  if (isPrivateHost(host)) throw internalError()
  const path = match[2] || '/'
  if (/^\/(?:api|v1)(?:\/|$)/i.test(path)) throw internalError()
  return text
}

function normalizeDocumentHit(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = {
    id: requiredText(value.id),
    title: requiredText(value.title),
    url: validatePublicDocumentUrl(value.url),
  }
  const summary = optionalText(value.summary)
  const dtype = optionalText(value.dtype)
  if (summary) result.summary = summary
  if (dtype) result.dtype = dtype
  return result
}

export function normalizeDocumentSearchResult(value, limit) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw internalError()
  const result = {}
  const query = optionalText(value.query)
  const personId = optionalText(value.personId)
  if (query) result.query = query
  if (personId) result.personId = personId

  if (value.documents !== undefined && value.documents !== null && !Array.isArray(value.documents)) {
    throw internalError()
  }
  const documents = (value.documents || [])
    .slice(0, boundedDocumentLimit(limit))
    .map(normalizeDocumentHit)
  result.documents = documents
  return result
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

function requestOptions() {
  return {
    format: 'json',
    passAsJson: true,
    returnHeaders: true,
  }
}

function parseResponse(response) {
  const status = Number(response && response.status)
  const parsed = response && response.parsed
  if (status >= 200 && status < 300) return parsed

  const code = safeErrorCode(status, parsed)
  throw new GatewayError(code, safeMessage(code))
}

function authorizationError() {
  const error = new Error('StarIntel authorization must be refreshed.')
  error.$type = 'authorization-error'
  error.$message = 'Please reconnect your StarIntel account.'
  return error
}

export function postJson(httpClient, origin, path, body) {
  const base = validateGatewayOrigin(origin)
  const safePath = validatePath(path)
  let response
  try {
    response = httpClient.postUrl(`${base}${safePath}`, body, requestOptions())
  } catch (_error) {
    throw new GatewayError('UPSTREAM_UNAVAILABLE', safeMessage('UPSTREAM_UNAVAILABLE'))
  }
  return parseResponse(response)
}

export function postJsonOptionalUser(httpClient, origin, path, body, vivContext) {
  const base = validateGatewayOrigin(origin)
  const safePath = validatePath(path)
  const signedIn = Boolean(vivContext && vivContext.accessToken)
  let response
  try {
    const method = signedIn ? 'oauthPostUrl' : 'postUrl'
    response = httpClient[method](`${base}${safePath}`, body, requestOptions())
  } catch (error) {
    if (signedIn && error && error.$type === 'authorization-error') throw error
    throw new GatewayError('UPSTREAM_UNAVAILABLE', safeMessage('UPSTREAM_UNAVAILABLE'))
  }

  if (signedIn && Number(response && response.status) === 401) {
    throw authorizationError()
  }
  return parseResponse(response)
}

export default {
  GatewayError,
  boundedDocumentLimit,
  buildDocumentSearchRequest,
  buildPersonResolveRequest,
  normalizeDocumentSearchResult,
  normalizePersonSearchResult,
  postJson,
  postJsonOptionalUser,
  validateGatewayOrigin,
}
