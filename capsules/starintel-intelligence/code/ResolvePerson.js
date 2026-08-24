import config from 'config'
import http from 'http'

import GatewayPolicy from './lib/GatewayPolicy.js'

export default function resolvePerson(input) {
  const request = GatewayPolicy.buildPersonResolveRequest(input && input.query)
  return GatewayPolicy.postJson(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/person/resolve',
    request,
  )
}
