import axios from 'axios';
import pino from 'pino';
import { CONFIG } from './config.js';
import { IncomingWhatsAppMessage } from './types.js';

const logger = pino({ level: CONFIG.logLevel });

export class WebhookClient {
  private url: string;
  private secret: string;

  constructor() {
    this.url = CONFIG.backendWebhookUrl;
    this.secret = CONFIG.gatewaySecret;
  }

  public async forwardMessage(payload: IncomingWhatsAppMessage): Promise<boolean> {
    const maxRetries = 3;
    let attempt = 0;

    while (attempt < maxRetries) {
      attempt++;
      try {
        const response = await axios.post(this.url, payload, {
          headers: {
            'Content-Type': 'application/json',
            'X-Gateway-Secret': this.secret,
          },
          timeout: 15000,
        });

        if (response.status >= 200 && response.status < 300) {
          logger.debug({ messageId: payload.messageId }, 'Successfully forwarded message to backend');
          return true;
        }
      } catch (err: any) {
        logger.warn(
          { attempt, error: err.message, messageId: payload.messageId },
          'Failed to forward message to backend webhook'
        );
        if (attempt < maxRetries) {
          await new Promise((res) => setTimeout(res, 1000 * attempt));
        }
      }
    }

    logger.error({ messageId: payload.messageId }, 'Max retries exceeded forwarding to backend webhook');
    return false;
  }
}
