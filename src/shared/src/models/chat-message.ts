/**
 * Role of a participant in a chat conversation.
 */
export type ChatRole = 'user' | 'assistant' | 'system';

/**
 * A citation linking an AI response back to a source.
 */
export interface Citation {
  title: string;
  url?: string;
  content?: string;
}

/**
 * A single chat message in a conversation.
 */
export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  citations?: Citation[];
  timestamp: string;
}

/**
 * A chat session containing a conversation thread.
 */
export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}
