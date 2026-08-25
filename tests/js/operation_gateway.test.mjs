import assert from 'node:assert/strict'
import test from 'node:test'

import {
  GatewayError,
  buildCommitRequest,
  buildPrepareRequest,
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
