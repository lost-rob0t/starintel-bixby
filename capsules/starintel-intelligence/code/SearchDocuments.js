import config from 'config'
import http from 'http'

import GatewayPolicy from './lib/GatewayPolicy.js'

export default function searchDocuments(input) {
  const request = GatewayPolicy.buildDocumentSearchRequest(input || {})
  const response = GatewayPolicy.postJsonOptionalUser(
    http,
    config.get('starintel.gateway.origin'),
    '/v1/bixby/documents/search',
    request,
    input && input.$vivContext,
  )
  return GatewayPolicy.normalizeDocumentSearchResult(response, request.limit)
}
