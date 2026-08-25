import config from 'config'
import http from 'http'

import OperationGateway from './lib/OperationGateway.js'

export default function commitTarget(input) {
  const request = OperationGateway.buildCommitRequest(input && input.draft)
  const response = OperationGateway.postAuthorized(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/targets/commit',
    request,
  )
  return OperationGateway.normalizeTargetReceipt(response)
}
