import { WASocket } from '@whiskeysockets/baileys';
import pino from 'pino';
import axios from 'axios';
import { CONFIG } from './config.js';
import { SendMediaMessageRequest, SendMessageResponse, SendTextMessageRequest } from './types.js';

const logger = pino({ level: CONFIG.logLevel });

export class MessageSender {
  private getSocket: () => WASocket | null;

  constructor(socketGetter: () => WASocket | null) {
    this.getSocket = socketGetter;
  }

  public async sendText(req: SendTextMessageRequest): Promise<SendMessageResponse> {
    const socket = this.getSocket();
    if (!socket) {
      return { success: false, error: 'WhatsApp socket not connected' };
    }

    try {
      const options: any = {};
      if (req.quotedMessageId) {
        // Can be used if quoted message is referenced
      }

      const sent = await socket.sendMessage(req.to, { text: req.text }, options);
      const messageId = sent?.key?.id;

      logger.info({ to: req.to, messageId }, 'Sent text message');
      return { success: true, messageId: messageId || undefined };
    } catch (err: any) {
      logger.error({ to: req.to, error: err.message }, 'Failed to send text message');
      return { success: false, error: err.message };
    }
  }

  public async sendMedia(req: SendMediaMessageRequest): Promise<SendMessageResponse> {
    const socket = this.getSocket();
    if (!socket) {
      return { success: false, error: 'WhatsApp socket not connected' };
    }

    try {
      let buffer: Buffer;

      if (req.mediaBase64) {
        buffer = Buffer.from(req.mediaBase64, 'base64');
      } else if (req.mediaUrl) {
        const response = await axios.get(req.mediaUrl, { responseType: 'arraybuffer' });
        buffer = Buffer.from(response.data);
      } else {
        return { success: false, error: 'No media content provided (url or base64 required)' };
      }

      let sent: any;

      if (req.mediaType === 'image') {
        sent = await socket.sendMessage(req.to, {
          image: buffer,
          caption: req.caption,
        });
      } else {
        sent = await socket.sendMessage(req.to, {
          document: buffer,
          mimetype: req.fileName?.endsWith('.pdf') ? 'application/pdf' : 'application/octet-stream',
          fileName: req.fileName || 'attachment.pdf',
          caption: req.caption,
        });
      }

      const messageId = sent?.key?.id;
      logger.info({ to: req.to, messageId, mediaType: req.mediaType }, 'Sent media message');
      return { success: true, messageId: messageId || undefined };
    } catch (err: any) {
      logger.error({ to: req.to, error: err.message }, 'Failed to send media message');
      return { success: false, error: err.message };
    }
  }
}
