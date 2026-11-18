import { test } from 'node:test';
import assert from 'node:assert';
import { unwrapActualMessage, getNormalizedWAMessage } from '../src/message-utils.js';

test('unwrapActualMessage returns standard message directly', () => {
  const msg = { conversation: 'Hello world' };
  const unwrapped = unwrapActualMessage(msg as any);
  assert.deepStrictEqual(unwrapped, msg);
});

test('unwrapActualMessage unwraps ephemeralMessage', () => {
  const inner = { imageMessage: { caption: 'Assignment screenshot' } };
  const msg = {
    ephemeralMessage: {
      message: inner,
    },
  };
  const unwrapped = unwrapActualMessage(msg as any);
  assert.deepStrictEqual(unwrapped, inner);
});

test('unwrapActualMessage unwraps viewOnceMessage and viewOnceMessageV2', () => {
  const innerImg = { imageMessage: { url: 'https://whatsapp.net/img.jpg' } };
  const v1 = {
    viewOnceMessage: {
      message: innerImg,
    },
  };
  assert.deepStrictEqual(unwrapActualMessage(v1 as any), innerImg);

  const innerDoc = { documentMessage: { fileName: 'homework.pdf' } };
  const v2 = {
    viewOnceMessageV2: {
      message: innerDoc,
    },
  };
  assert.deepStrictEqual(unwrapActualMessage(v2 as any), innerDoc);
});

test('unwrapActualMessage handles nested ephemeral and viewOnce wrappers', () => {
  const innerImg = { imageMessage: { caption: 'Disappearing view once homework' } };
  const nested = {
    ephemeralMessage: {
      message: {
        viewOnceMessage: {
          message: innerImg,
        },
      },
    },
  };
  assert.deepStrictEqual(unwrapActualMessage(nested as any), innerImg);
});

test('getNormalizedWAMessage produces WAMessage with unwrapped message', () => {
  const innerDoc = { documentMessage: { fileName: 'lab.pdf' } };
  const waMsg: any = {
    key: { remoteJid: '120363028392039203@g.us', id: 'MSG123' },
    message: {
      viewOnceMessage: {
        message: innerDoc,
      },
    },
  };

  const normalized = getNormalizedWAMessage(waMsg);
  assert.strictEqual(normalized.key.id, 'MSG123');
  assert.deepStrictEqual(normalized.message, innerDoc);
});
