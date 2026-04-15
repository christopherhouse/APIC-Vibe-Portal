/**
 * The kind (protocol/style) of an API.
 */
export enum ApiKind {
  REST = 'rest',
  GraphQL = 'graphql',
  GRPC = 'grpc',
  SOAP = 'soap',
  WebSocket = 'websocket',
  Webhook = 'webhook',
}
