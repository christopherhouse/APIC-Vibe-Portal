/**
 * Request DTO for the chat endpoint.
 */
export interface ChatRequest {
  sessionId?: string;
  message: string;
}
