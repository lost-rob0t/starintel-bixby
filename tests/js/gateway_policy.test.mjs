import assert from 'node:assert/strict'
import test from 'node:test'

import {
  GatewayError,
  boundedDocumentLimit,
  buildDocumentSearchRequest,
  buildPersonResolveRequest,
  postJson,
  validateGatewayOrigin,
} from '../../capsules/starintel-intelligence/code/lib/GatewayPolicy.js'

test('gateway origin requires public https and removes a trailing slash', () => {
  assert.equal(validateGatewayOrigin('https://gateway.example/'), 'https://gateway.example')
})

test('gateway origin rejects insecure and private destinations', () => {
  for (const origin of [
    'http://gateway.example',
    'https://ingest.star.intel',
    'https://localhost',
    'https://127.0.0.1',
    'https://10.0.0.5',
    'https://172.20.0.5',
    'https://192.168.1.5',
    'https://169.254.1.5',
  ]) {
    assert.throws(() => validateGatewayOrigin(origin), GatewayError, origin)
  }
})

test('document result limit defaults to five and is clamped to one through ten', () => {
  assert.equal(boundedDocumentLimit(undefined), 5)
  assert.equal(boundedDocumentLimit(null), 5)
  assert.equal(boundedDocumentLimit(0), 1)
  assert.equal(boundedDocumentLimit(3), 3)
  assert.equal(boundedDocumentLimit(99), 10)
})

test('person request accepts only a trimmed non-empty query', () => {
  assert.deepEqual(buildPersonResolveRequest(' John Smith '), { query: 'John Smith' })
  for (const query of [undefined, null, '', '   ']) {
    assert.throws(() => buildPersonResolveRequest(query), error => error instanceof GatewayError && error.code === 'INVALID_REQUEST')
  }
})

test('document request requires query or person context and emits only bounded public-contract fields', () => {
  assert.deepEqual(
    buildDocumentSearchRequest({ query: ' reports ', personId: ' person-42 ', dtype: ' pdf ', limit: 999, ignored: 'secret' }),
    { query: 'reports', personId: 'person-42', dtype: 'pdf', limit: 10 },
  )
  assert.deepEqual(buildDocumentSearchRequest({ personId: 'person-42' }), { personId: 'person-42', limit: 5 })
  assert.throws(
    () => buildDocumentSearchRequest({ query: ' ', personId: ' ' }),
    error => error instanceof GatewayError && error.code === 'INVALID_REQUEST',
  )
})

test('postJson uses JSON POST with headers returned for explicit error handling', () => {
  const calls = []
  const http = {
    postUrl(url, body, options) {
      calls.push({ url, body, options })
      return { status: 200, parsed: { ok: true } }
    },
  }

  const result = postJson(http, 'https://gateway.example', '/v1/bixby/person/resolve', { query: 'John Smith' })

  assert.deepEqual(result, { ok: true })
  assert.deepEqual(calls, [{
    url: 'https://gateway.example/v1/bixby/person/resolve',
    body: { query: 'John Smith' },
    options: { format: 'json', passAsJson: true, returnHeaders: true },
  }])
})

test('postJson preserves only allow-listed gateway error codes', () => {
  const http = {
    postUrl() {
      return { status: 404, parsed: { error: { code: 'PERSON_NOT_FOUND', message: 'internal detail' } } }
    },
  }

  assert.throws(
    () => postJson(http, 'https://gateway.example', '/v1/bixby/person/resolve', {}),
    error => error instanceof GatewayError && error.code === 'PERSON_NOT_FOUND' && !error.message.includes('internal detail'),
  )
})

test('postJson maps unknown gateway errors and transport exceptions to stable safe codes', () => {
  const unknown = { postUrl: () => ({ status: 500, parsed: { error: { code: 'RAW_LISP_CONDITION' } } }) }
  assert.throws(
    () => postJson(unknown, 'https://gateway.example', '/v1/bixby/person/resolve', {}),
    error => error instanceof GatewayError && error.code === 'INTERNAL_ERROR',
  )

  const offline = { postUrl: () => { throw new Error('socket backend-secret') } }
  assert.throws(
    () => postJson(offline, 'https://gateway.example', '/v1/bixby/person/resolve', {}),
    error => error instanceof GatewayError && error.code === 'UPSTREAM_UNAVAILABLE' && !error.message.includes('backend-secret'),
  )
})
