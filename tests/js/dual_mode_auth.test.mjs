import assert from 'node:assert/strict'
import test from 'node:test'

import { postJsonOptionalUser } from '../../capsules/starintel-intelligence/code/lib/GatewayPolicy.js'

const ORIGIN = 'https://gateway.example'
const PATH = '/v1/bixby/person/resolve'
const BODY = { query: 'John Smith' }

test('guest request uses ordinary JSON POST and never OAuth', () => {
  const calls = []
  const http = {
    postUrl(url, body, options) {
      calls.push({ method: 'postUrl', url, body, options })
      return { status: 200, parsed: { ok: true } }
    },
    oauthPostUrl() {
      assert.fail('guest requests must not use OAuth transport')
    },
  }

  const result = postJsonOptionalUser(http, ORIGIN, PATH, BODY, undefined)

  assert.deepEqual(result, { ok: true })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].method, 'postUrl')
  assert.deepEqual(calls[0].body, BODY)
})

test('signed-in request uses Bixby-managed OAuth POST without copying token into request data', () => {
  const calls = []
  const context = {
    accessToken: 'super-secret-user-token',
    bixbyUserId: 'must-not-become-starintel-identity',
    locale: 'en-US',
    device: { model: 'phone' },
  }
  const http = {
    postUrl() {
      assert.fail('signed-in requests must not silently downgrade to guest transport')
    },
    oauthPostUrl(url, body, options) {
      calls.push({ method: 'oauthPostUrl', url, body, options })
      return { status: 200, parsed: { ok: true } }
    },
  }

  const result = postJsonOptionalUser(http, ORIGIN, PATH, BODY, context)

  assert.deepEqual(result, { ok: true })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].method, 'oauthPostUrl')
  const serialized = JSON.stringify(calls[0])
  assert.equal(serialized.includes(context.accessToken), false)
  assert.equal(serialized.includes(context.bixbyUserId), false)
  assert.equal(serialized.includes('en-US'), false)
})

test('authenticated 401 becomes Bixby authorization-error and is never retried anonymously', () => {
  let guestCalls = 0
  let oauthCalls = 0
  const http = {
    postUrl() {
      guestCalls += 1
      return { status: 200, parsed: { public: true } }
    },
    oauthPostUrl() {
      oauthCalls += 1
      return { status: 401, parsed: { error: { code: 'UNAUTHORIZED' } } }
    },
  }

  assert.throws(
    () => postJsonOptionalUser(http, ORIGIN, PATH, BODY, { accessToken: 'expired' }),
    error => error && error.$type === 'authorization-error',
  )
  assert.equal(oauthCalls, 1)
  assert.equal(guestCalls, 0)
})

test('authenticated forbidden response remains forbidden rather than requesting login', () => {
  const http = {
    oauthPostUrl() {
      return { status: 403, parsed: { error: { code: 'FORBIDDEN' } } }
    },
  }

  assert.throws(
    () => postJsonOptionalUser(http, ORIGIN, PATH, BODY, { accessToken: 'valid-but-insufficient' }),
    error => error && error.code === 'FORBIDDEN' && error.$type !== 'authorization-error',
  )
})
