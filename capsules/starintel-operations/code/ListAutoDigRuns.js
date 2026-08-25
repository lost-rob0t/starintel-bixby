import config from 'config'
import http from 'http'

import OperationGateway from './lib/OperationGateway.js'

export default function listAutoDigRuns() {
  const response = OperationGateway.postAuthorized(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/autodig/runs',
    {},
  )
  return OperationGateway.normalizeAutoDigRunList(response)
}
