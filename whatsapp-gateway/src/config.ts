import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '../.env') });
dotenv.config(); // fallback to local .env

export const CONFIG = {
  port: parseInt(process.env.GATEWAY_PORT || '3000', 10),
  backendWebhookUrl: process.env.BACKEND_WEBHOOK_URL || 'http://localhost:8000/api/v1/webhook/whatsapp',
  gatewaySecret: process.env.WHATSAPP_GATEWAY_SECRET || 'chirp-shared-gateway-secret-key-12345',
  authDir: process.env.WHATSAPP_AUTH_DIR || path.resolve(process.cwd(), 'auth_info_baileys'),
  logLevel: process.env.LOG_LEVEL || 'info',
};
