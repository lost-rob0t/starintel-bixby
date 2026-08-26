import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const requirements = JSON.parse(
  await readFile(
    new URL('../../capsules/starintel-operations/auth.requirements.json', import.meta.url),
    'utf8',
  ),
)

test('Operations requests the canonical StarIntel target dispatch scope', () => {
  assert.ok(requirements.requiredScopes.includes('targets:dispatch'))
  assert.ok(!requirements.requiredScopes.includes('starintel.targets.write'))
})

test('Operations auth metadata does not resurrect a standalone Bixby gateway identity', () => {
  assert.equal(requirements.principalMode, 'user')
  assert.equal(requirements.forwardVivContext, false)
  assert.doesNotMatch(requirements.notes, /standalone gateway|gateway service identity/i)
})