import { downloadMediaMessage, WAMessage } from '@whiskeysockets/baileys';
import pino from 'pino';
import { CONFIG } from './config.js';
import { IncomingMediaAttachment } from './types.js';

const logger = pino({ level: CONFIG.logLevel });

export async function extractMediaFromMessage(
  msg: WAMessage
): Promise<IncomingMediaAttachment | null> {
  const message = msg.message;
  if (!message) return null;

  try {
    const isImage = !!message.imageMessage;
    const isDocument = !!message.documentMessage;

    if (!isImage && !isDocument) {
      return null;
    }

    const buffer = await downloadMediaMessage(
      msg,
      'buffer',
      {},
      {
        logger: logger as any,
        reuploadRequest: () => Promise.reject(new Error('Cannot re-upload')),
      }
    );

    if (!buffer || buffer.length === 0) {
      return null;
    }

    if (isImage) {
      const img = message.imageMessage!;
      return {
        fileName: 'image.jpg',
        mimeType: img.mimetype || 'image/jpeg',
        fileSize: buffer.length,
        dataBase64: buffer.toString('base64'),
        caption: img.caption || undefined,
      };
    }

    if (isDocument) {
      const doc = message.documentMessage!;
      return {
        fileName: doc.fileName || 'document.pdf',
        mimeType: doc.mimetype || 'application/pdf',
        fileSize: buffer.length,
        dataBase64: buffer.toString('base64'),
        caption: doc.caption || undefined,
      };
    }

    return null;
  } catch (error: any) {
    logger.error({ error: error.message }, 'Failed to download media message');
    return null;
  }
}
