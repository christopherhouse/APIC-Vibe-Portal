import { ChatMessage } from '../models/chat-message.js';

/**
 * Response DTO for the chat endpoint.
 */
export interface ChatResponse {
  sessionId: string;
  message: ChatMessage;
}
