// 录制失败必须释放已创建的画布视频轨道，避免无声遗留资源。
import test from 'node:test';
import assert from 'node:assert/strict';
import { startRecorder } from '../../frontend/js/share-capture.js';

for (const stage of ['constructor', 'start']) {
  test(`recording failure at ${stage} stops its stream`, () => {
    const original = globalThis.MediaRecorder;
    let stopped = 0;
    const track = { stop() { stopped += 1; } };
    const stream = { getVideoTracks: () => [track], getTracks: () => [track] };
    const canvas = /** @type {HTMLCanvasElement} */ (/** @type {unknown} */ ({ captureStream: () => stream }));
    globalThis.MediaRecorder = /** @type {typeof MediaRecorder} */ (/** @type {unknown} */ (class {
      constructor() { if (stage === 'constructor') throw new Error('模拟构造失败'); }
      start() { throw new Error('模拟启动失败'); }
    }));
    try {
      assert.throws(() => startRecorder(canvas, 'video/webm'), /模拟/);
      assert.equal(stopped, 1);
    } finally {
      if (original === undefined) delete globalThis.MediaRecorder;
      else globalThis.MediaRecorder = original;
    }
  });
}
