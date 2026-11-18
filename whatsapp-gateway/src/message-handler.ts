import { WAMessage, isJidGroup } from '@whiskeysockets/baileys';
import pino from 'pino';
import { CONFIG } from './config.js';
import { extractMediaFromMessage } from './media-handler.js';
import { unwrapActualMessage } from './message-utils.js';
import { IncomingWhatsAppMessage } from './types.js';
import { WebhookClient } from './webhook-client.js';

const logger = pino({ level: CONFIG.logLevel });

export class MessageHandler {
  private webhookClient: WebhookClient;

  constructor(webhookClient: WebhookClient) {
    this.webhookClient = webhookClient;
  }

  public async handleMessage(msg: WAMessage): Promise<void> {
    // Ignore status broadcasts and messages sent by the bot itself
    if (!msg.key || msg.key.fromMe || msg.key.remoteJid === 'status@broadcast') {
      return;
    }

    const remoteJid = msg.key.remoteJid;
    if (!remoteJid) return;

    const isGroup = !!isJidGroup(remoteJid);
    const senderJid = isGroup ? msg.key.participant || remoteJid : remoteJid;

    // Recursively unwrap ephemeral, view-once, and document-with-caption wrappers
    const messageContent = unwrapActualMessage(msg.message);

    if (!messageContent) return;

    // Check for forwarded message context
    const contextInfo =
      messageContent.extendedTextMessage?.contextInfo ||
      messageContent.imageMessage?.contextInfo ||
      messageContent.documentMessage?.contextInfo;

    const isForwarded = !!contextInfo?.isForwarded;

    // Extract text content
    const text =
      messageContent.conversation ||
      messageContent.extendedTextMessage?.text ||
      messageContent.imageMessage?.caption ||
      messageContent.documentMessage?.caption ||
      undefined;

    // Quoted message context if available
    let quotedMessage: IncomingWhatsAppMessage['quotedMessage'] = undefined;
    if (contextInfo?.stanzaId && contextInfo.participant) {
      quotedMessage = {
        messageId: contextInfo.stanzaId,
        senderJid: contextInfo.participant,
        text: contextInfo.quotedMessage?.conversation ||
          contextInfo.quotedMessage?.extendedTextMessage?.text ||
          undefined,
      };
    }

    // Extract media if present
    const media = await extractMediaFromMessage(msg);

    const payload: IncomingWhatsAppMessage = {
      messageId: msg.key.id || `${Date.now()}`,
      chatJid: remoteJid,
      senderJid: senderJid,
      senderName: msg.pushName || undefined,
      isGroup,
      isForwarded,
      timestamp: typeof msg.messageTimestamp === 'number'
        ? msg.messageTimestamp
        : Number(msg.messageTimestamp) || Math.floor(Date.now() / 1000),
      text,
      caption: media?.caption,
      quotedMessage,
      media: media || undefined,
    };

    logger.info(
      {
        messageId: payload.messageId,
        chatJid: payload.chatJid,
        isGroup: payload.isGroup,
        hasMedia: !!payload.media,
        hasText: !!payload.text,
      },
      'Processing incoming WhatsApp message'
    );

    await this.webhookClient.forwardMessage(payload);
  }
}
