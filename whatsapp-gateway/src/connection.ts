import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  WASocket,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import qrcode from 'qrcode-terminal';
import pino from 'pino';
import fs from 'fs';
import { CONFIG } from './config.js';
import { GatewayStatus } from './types.js';
import { MessageHandler } from './message-handler.js';

const logger = pino({ level: CONFIG.logLevel });

export class WhatsAppConnection {
  private socket: WASocket | null = null;
  private messageHandler: MessageHandler;
  private currentStatus: GatewayStatus = {
    status: 'disconnected',
    connectedPhone: null,
    qrCode: null,
    uptime: 0,
  };
  private startTime: number = Date.now();
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;

  constructor(messageHandler: MessageHandler) {
    this.messageHandler = messageHandler;
  }

  public getSocket(): WASocket | null {
    return this.socket;
  }

  public getStatus(): GatewayStatus {
    return {
      ...this.currentStatus,
      uptime: Math.floor((Date.now() - this.startTime) / 1000),
    };
  }

  public async connect(): Promise<void> {
    if (!fs.existsSync(CONFIG.authDir)) {
      fs.mkdirSync(CONFIG.authDir, { recursive: true });
    }

    this.currentStatus.status = 'connecting';
    logger.info('Initializing Baileys WhatsApp connection...');

    const { state, saveCreds } = await useMultiFileAuthState(CONFIG.authDir);
    const { version } = await fetchLatestBaileysVersion();

    const socket = makeWASocket({
      version,
      auth: state,
      printQRInTerminal: false,
      logger: pino({ level: 'warn' }) as any,
      browser: ['Chirp Academic Bot', 'Chrome', '1.0.0'],
      syncFullHistory: false,
    });

    this.socket = socket;

    socket.ev.on('creds.update', saveCreds);

    socket.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        this.currentStatus.qrCode = qr;
        this.currentStatus.status = 'qr_ready';
        logger.info('Scan QR Code to authenticate WhatsApp session:');
        qrcode.generate(qr, { small: true });
      }

      if (connection === 'close') {
        const statusCode = (lastDisconnect?.error as Boom)?.output?.statusCode;
        const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
        this.currentStatus.status = 'disconnected';
        this.currentStatus.connectedPhone = null;

        logger.warn(
          { statusCode, shouldReconnect },
          'WhatsApp connection closed'
        );

        if (shouldReconnect) {
          this.reconnectAttempts++;
          const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
          logger.info(`Reconnecting in ${delay / 1000} seconds... (attempt ${this.reconnectAttempts})`);
          setTimeout(() => this.connect(), delay);
        } else {
          logger.error('WhatsApp session logged out. Manual re-authentication with QR code required.');
          this.currentStatus.qrCode = null;
        }
      } else if (connection === 'open') {
        this.reconnectAttempts = 0;
        this.currentStatus.status = 'connected';
        this.currentStatus.qrCode = null;
        this.currentStatus.connectedPhone = socket.user?.id || null;
        logger.info(
          { user: socket.user },
          'WhatsApp connection established successfully!'
        );
      }
    });

    socket.ev.on('messages.upsert', async ({ messages, type }) => {
      if (type !== 'notify') return;

      for (const msg of messages) {
        try {
          await this.messageHandler.handleMessage(msg);
        } catch (err: any) {
          logger.error({ error: err.message }, 'Error in message handler');
        }
      }
    });
  }
}
