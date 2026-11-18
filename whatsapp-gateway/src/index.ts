import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import pino from 'pino';
import { CONFIG } from './config.js';
import { WebhookClient } from './webhook-client.js';
import { MessageHandler } from './message-handler.js';
import { WhatsAppConnection } from './connection.js';
import { MessageSender } from './sender.js';
import { SendMediaMessageRequest, SendTextMessageRequest } from './types.js';

const logger = pino({ level: CONFIG.logLevel });
const app = express();

app.use(cors());
app.use(express.json({ limit: '50mb' }));

const webhookClient = new WebhookClient();
const messageHandler = new MessageHandler(webhookClient);
const connection = new WhatsAppConnection(messageHandler);
const sender = new MessageSender(() => connection.getSocket());

// Authentication middleware for incoming requests from backend
const authMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  const secret = req.headers['x-gateway-secret'];
  if (!secret || secret !== CONFIG.gatewaySecret) {
    res.status(401).json({ error: 'Unauthorized: Invalid or missing X-Gateway-Secret' });
    return;
  }
  next();
};

// Health and status endpoints
app.get('/health', (_req: Request, res: Response) => {
  const status = connection.getStatus();
  res.json({
    status: 'ok',
    gateway: status,
  });
});

app.get('/status', (_req: Request, res: Response) => {
  res.json(connection.getStatus());
});

// Outbound send endpoints
app.post('/send/text', authMiddleware, async (req: Request, res: Response) => {
  const body = req.body as SendTextMessageRequest;
  if (!body.to || !body.text) {
    res.status(400).json({ error: 'Missing required fields: to, text' });
    return;
  }

  const result = await sender.sendText(body);
  if (!result.success) {
    res.status(500).json(result);
    return;
  }
  res.json(result);
});

app.post('/send/media', authMiddleware, async (req: Request, res: Response) => {
  const body = req.body as SendMediaMessageRequest;
  if (!body.to || (!body.mediaUrl && !body.mediaBase64) || !body.mediaType) {
    res.status(400).json({ error: 'Missing required fields: to, mediaUrl/mediaBase64, mediaType' });
    return;
  }

  const result = await sender.sendMedia(body);
  if (!result.success) {
    res.status(500).json(result);
    return;
  }
  res.json(result);
});

// Start Gateway
async function main() {
  app.listen(CONFIG.port, () => {
    logger.info(`WhatsApp Gateway API listening on port ${CONFIG.port}`);
  });

  // Start WhatsApp connection (only in production or when explicitly enabled; avoid connecting in purely mock/test environments)
  if (process.env.AUTO_CONNECT_WHATSAPP !== 'false') {
    connection.connect().catch((err) => {
      logger.error({ error: err.message }, 'Failed to initialize WhatsApp connection');
    });
  } else {
    logger.info('AUTO_CONNECT_WHATSAPP is disabled; running gateway API in standalone mode.');
  }
}

main().catch((err) => {
  logger.fatal({ error: err.message }, 'Fatal error during startup');
  process.exit(1);
});
