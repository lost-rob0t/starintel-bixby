import assert from 'node:assert/strict'
import test from 'node:test'

import {
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
} from '../../capsules/starintel-operations/code/lib/OperationGateway.js'

test('Operations gateway origin rejects insecure and private destinations', () => {
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
  assert.equal(validateGatewayOrigin('https://gateway.example/'), 'https://gateway.example')
})

test('prepare request emits only user-facing target fields', () => {
  assert.deepEqual(
    buildPrepareRequest({
      subject: ' John Smith ',
      targetType: ' person ',
      actor: ' BBPD ',
      routingKey: 'forbidden',
      exchange: 'forbidden',
      backendUrl: 'https://private.example',
    }),
    { subject: 'John Smith', targetType: 'person', actor: 'BBPD' },
  )
})

test('commit request carries only the opaque prepared draft id', () => {
  assert.deepEqual(
    buildCommitRequest({ draftId: ' draft-42 ', subject: 'John Smith', actor: 'BBPD', raw: { secret: true } }),
    { draftId: 'draft-42' },
  )
})

test('target draft normalization strips internal routing and backend fields', () => {
  assert.deepEqual(normalizeTargetDraft({
    draftId: 'draft-42',
    subject: 'John Smith',
    targetType: 'person',
    actor: 'BBPD',
    routingKey: 'private.route',
    exchange: 'private.exchange',
    canonicalActorId: 'internal-actor-id',
    backend: { host: 'private' },
  }), {
    draftId: 'draft-42',
    subject: 'John Smith',
    targetType: 'person',
    actor: 'BBPD',
  })
})

test('target receipt normalization strips internal acceptance and transport fields', () => {
  assert.deepEqual(normalizeTargetReceipt({
    receiptId: 'receipt-42',
    status: 'accepted',
    acceptanceId: 'internal-acceptance-id',
    fingerprint: 'internal-fingerprint',
    routingKey: 'private.route',
    raw: { secret: true },
  }), {
    receiptId: 'receipt-42',
    status: 'accepted',
  })
})

test('Auto-Dig request builders accept only target or durable run identity', () => {
  assert.deepEqual(buildStartRequest('  John Smith  '), { target: 'John Smith' })
  assert.deepEqual(buildRunRequest(' run-42 '), { runId: 'run-42' })
  assert.throws(() => buildStartRequest(''), GatewayError)
  assert.throws(() => buildRunRequest(''), GatewayError)
})

test('Auto-Dig normalization strips workspace and worker lease internals', () => {
  assert.deepEqual(normalizeAutoDigRun({
    runId: 'run-42',
    requestId: 'request-42',
    target: 'John Smith',
    status: 'active',
    workspaceId: 'private-workspace',
    workerId: 'private-worker',
    leaseId: 'private-lease',
    heartbeatAt: 1234,
    outcome: { internal: true },
  }), {
    runId: 'run-42',
    requestId: 'request-42',
    target: 'John Smith',
    status: 'active',
  })
})

test('Auto-Dig run lists are bounded and normalized item by item', () => {
  const runs = Array.from({ length: 25 }, (_, index) => ({
    runId: `run-${index}`,
    status: 'queued',
    workerId: `worker-${index}`,
  }))
  const normalized = normalizeAutoDigRunList({ runs })
  assert.equal(normalized.runs.length, 20)
  assert.deepEqual(normalized.runs[0], { runId: 'run-0', status: 'queued' })
})

test('authorized transport uses oauthPostUrl only', () => {
  const calls = []
  const http = {
    oauthPostUrl(url, body, options) {
      calls.push({ method: 'oauthPostUrl', url, body, options })
      return { status: 200, parsed: { draftId: 'draft-42', subject: 'John Smith' } }
    },
    postUrl() {
      throw new Error('guest transport must never be used for Operations mutation')
    },
  }

  const result = postAuthorized(
    http,
    'https://gateway.example',
    '/v1/bixby/targets/prepare',
    { subject: 'John Smith' },
  )

  assert.deepEqual(result, { draftId: 'draft-42', subject: 'John Smith' })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].method, 'oauthPostUrl')
})

test('Auto-Dig public routes use authorized transport and arbitrary routes fail closed', () => {
  const calls = []
  const http = {
    oauthPostUrl(url, body) {
      calls.push({ url, body })
      return { status: 200, parsed: { runId: 'run-42', status: 'queued' } }
    },
  }
  assert.deepEqual(
    postAuthorized(http, 'https://gateway.example', '/v1/bixby/autodig/start', { target: 'John Smith' }),
    { runId: 'run-42', status: 'queued' },
  )
  assert.equal(calls.length, 1)
  assert.throws(
    () => postAuthorized(http, 'https://gateway.example', '/v1/bixby/autodig/admin', {}),
    error => error instanceof GatewayError && error.code === 'INVALID_REQUEST',
  )
})

test('Auto-Dig capability and run errors remain stable and hide upstream details', () => {
  const capabilityMissing = {
    oauthPostUrl() {
      return {
        status: 503,
        parsed: { error: { code: 'AUTODIG_CAPABILITY_UNAVAILABLE', message: 'private Quasar detail' } },
      }
    },
  }
  assert.throws(
    () => postAuthorized(capabilityMissing, 'https://gateway.example', '/v1/bixby/autodig/status', {}),
    error => error instanceof GatewayError &&
      error.code === 'AUTODIG_CAPABILITY_UNAVAILABLE' &&
      !error.message.includes('private Quasar detail'),
  )

  const missingRun = {
    oauthPostUrl() {
      return {
        status: 404,
        parsed: { error: { code: 'AUTODIG_RUN_NOT_FOUND', message: 'workspace private' } },
      }
    },
  }
  assert.throws(
    () => postAuthorized(missingRun, 'https://gateway.example', '/v1/bixby/autodig/run', { runId: 'run-x' }),
    error => error instanceof GatewayError && error.code === 'AUTODIG_RUN_NOT_FOUND' && !error.message.includes('workspace private'),
  )
})

test('401 becomes Bixby authorization-error and unknown upstream details are not reflected', () => {
  const expired = {
    oauthPostUrl() {
      return { status: 401, parsed: { error: { code: 'TOKEN_EXPIRED', message: 'secret provider detail' } } }
    },
  }
  assert.throws(
    () => postAuthorized(expired, 'https://gateway.example', '/v1/bixby/targets/prepare', {}),
    error => error && error.$type === 'authorization-error' && !String(error.$message).includes('secret provider detail'),
  )

  const broken = {
    oauthPostUrl() {
      return { status: 500, parsed: { error: { code: 'RAW_RMQ_EXCEPTION', message: 'rabbitmq host secret' } } }
    },
  }
  assert.throws(
    () => postAuthorized(broken, 'https://gateway.example', '/v1/bixby/targets/prepare', {}),
    error => error instanceof GatewayError && error.code === 'INTERNAL_ERROR' && !error.message.includes('rabbitmq host secret'),
  )
})
