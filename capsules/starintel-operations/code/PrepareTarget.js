import config from 'config'
import http from 'http'

import OperationGateway from './lib/OperationGateway.js'

export default function prepareTarget(input) {
  const request = OperationGateway.buildPrepareRequest(input)
  const response = OperationGateway.postAuthorized(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/targets/prepare',
    request,
  )
  return OperationGateway.normalizeTargetDraft(response)
}
