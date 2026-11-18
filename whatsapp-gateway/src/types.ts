export type ConnectionStatus = 'disconnected' | 'connecting' | 'qr_ready' | 'connected' | 'logged_out';

export interface GatewayStatus {
  status: ConnectionStatus;
  connectedPhone: string | null;
  qrCode: string | null;
  uptime: number;
}

export interface IncomingMediaAttachment {
  fileName?: string;
  mimeType: string;
  fileSize?: number;
  dataBase64: string; // Base64 encoded file content
  caption?: string;
}

export interface IncomingWhatsAppMessage {
  messageId: string;
  chatJid: string;
  senderJid: string;
  senderName?: string;
  isGroup: boolean;
  isForwarded: boolean;
  timestamp: number;
  text?: string;
  caption?: string;
  quotedMessage?: {
    messageId: string;
    senderJid: string;
    text?: string;
  };
  media?: IncomingMediaAttachment;
}

export interface SendTextMessageRequest {
  to: string;
  text: string;
  quotedMessageId?: string;
}

export interface SendMediaMessageRequest {
  to: string;
  mediaUrl?: string;
  mediaBase64?: string;
  mediaType: 'image' | 'document';
  fileName?: string;
  caption?: string;
  quotedMessageId?: string;
}

export interface SendMessageResponse {
  success: boolean;
  messageId?: string;
  error?: string;
}
