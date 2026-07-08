const LEVELS = ['debug', 'info', 'warn', 'error'];

function shouldPrint(current, target) {
  return LEVELS.indexOf(target) >= LEVELS.indexOf(current);
}

export function createLogger(level = 'info') {
  const current = LEVELS.includes(level) ? level : 'info';

  return {
    debug: (...args) => shouldPrint(current, 'debug') && console.log('[wechat][debug]', ...args),
    info: (...args) => shouldPrint(current, 'info') && console.log('[wechat][info]', ...args),
    warn: (...args) => shouldPrint(current, 'warn') && console.warn('[wechat][warn]', ...args),
    error: (...args) => shouldPrint(current, 'error') && console.error('[wechat][error]', ...args)
  };
}
