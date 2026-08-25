import config from 'config'
import http from 'http'

import OperationGateway from './lib/OperationGateway.js'

export default function startAutoDig(input) {
  const response = OperationGateway.postAuthorized(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/autodig/start',
    OperationGateway.buildStartRequest(input.target),
  )
  return OperationGateway.normalizeAutoDigRun(response)
}
