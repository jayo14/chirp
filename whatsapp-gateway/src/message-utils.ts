import { proto, WAMessage } from '@whiskeysockets/baileys';

/**
 * Recursively unwraps ephemeral, view-once, and document-with-caption wrappers
 * to expose the actual inner message content (text, image, document, video, etc.).
 */
export function unwrapActualMessage(
  rawMessage: proto.IMessage | null | undefined
): proto.IMessage | undefined {
  if (!rawMessage) return undefined;

  let current: any = rawMessage;
  let depth = 0;

  while (current && depth < 5) {
    if (current.ephemeralMessage?.message) {
      current = current.ephemeralMessage.message;
    } else if (current.viewOnceMessage?.message) {
      current = current.viewOnceMessage.message;
    } else if (current.viewOnceMessageV2?.message) {
      current = current.viewOnceMessageV2.message;
    } else if (current.viewOnceMessageV2Extension?.message) {
      current = current.viewOnceMessageV2Extension.message;
    } else if (current.documentWithCaptionMessage?.message) {
      current = current.documentWithCaptionMessage.message;
    } else {
      break;
    }
    depth++;
  }

  return current as proto.IMessage;
}

/**
 * Returns a normalized WAMessage copy whose .message is fully unwrapped.
 * This ensures Baileys downloadMediaMessage can locate media keys.
 */
export function getNormalizedWAMessage(msg: WAMessage): WAMessage {
  const unwrapped = unwrapActualMessage(msg.message);
  if (unwrapped === msg.message) {
    return msg;
  }
  return {
    ...msg,
    message: unwrapped,
  };
}
