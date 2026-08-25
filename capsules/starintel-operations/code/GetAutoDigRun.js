import config from 'config'
import http from 'http'

import OperationGateway from './lib/OperationGateway.js'

export default function getAutoDigRun(input) {
  const response = OperationGateway.postAuthorized(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/autodig/run',
    OperationGateway.buildRunRequest(input.runId),
  )
  return OperationGateway.normalizeAutoDigRun(response)
}
