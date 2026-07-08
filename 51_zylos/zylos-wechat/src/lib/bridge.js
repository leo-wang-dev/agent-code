import { execFile } from 'node:child_process';

const MAX_ATTEMPTS = 2;

function parseJsonMaybe(text) {
  if (!text) return null;
  const trimmed = text.trim();
  if (!trimmed || (!trimmed.startsWith('{') && !trimmed.startsWith('['))) {
    return null;
  }

  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function getC4Failure(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return null;
  }

  const rejected =
    payload.ok === false ||
    payload.accepted === false ||
    payload.rejected === true ||
    payload.reject === true ||
    payload.status === 'error' ||
    payload.status === 'rejected';

  if (!rejected) {
    return null;
  }

  return {
    message: String(
      payload.error ||
      payload.message ||
      payload.reason ||
      payload.stderr ||
      'C4 rejected message'
    ),
    retryable: payload.retryable === true,
    details: payload,
  };
}

function runReceive(scriptPath, args) {
  return new Promise((resolve, reject) => {
    execFile('node', args, { encoding: 'utf8' }, (error, stdout, stderr) => {
      if (error) {
        error.stderr = stderr?.trim() || '';
        error.stdout = stdout?.trim() || '';
        reject(error);
        return;
      }

      resolve({
        stdout: stdout?.trim() || '',
        stderr: stderr?.trim() || '',
      });
    });
  });
}

export async function sendToC4({ scriptPath, channel = 'wechat', endpoint, content, logger }) {
  const args = [
    scriptPath,
    '--channel', channel,
    '--endpoint', endpoint,
    '--json',
    '--content', content,
  ];

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    let result;

    try {
      result = await runReceive(scriptPath, args);
    } catch (error) {
      if (attempt < MAX_ATTEMPTS) {
        logger?.warn?.('c4 receive failed, retrying once', error.message, error.stderr || '');
        continue;
      }

      logger?.error?.('c4 receive failed', error.message, error.stderr || '');
      throw error;
    }

    if (result.stdout) {
      logger?.debug?.('c4 response', result.stdout);
    }
    if (result.stderr) {
      logger?.debug?.('c4 stderr', result.stderr);
    }

    const failure = getC4Failure(parseJsonMaybe(result.stdout));
    if (!failure) {
      return result.stdout;
    }

    const error = new Error(failure.message);
    error.details = failure.details;

    if (attempt < MAX_ATTEMPTS && failure.retryable) {
      logger?.warn?.('c4 receive rejected with retryable error, retrying once', failure.message);
      continue;
    }

    logger?.error?.('c4 receive rejected', failure.message);
    throw error;
  }

  throw new Error('c4 receive failed after retries');
}
