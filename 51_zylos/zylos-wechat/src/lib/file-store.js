import { chmod, mkdir, readFile, rename, rm, unlink, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';

export async function ensureDir(path) {
  await mkdir(path, { recursive: true });
}

export async function readJsonFile(path, fallback = null) {
  try {
    const raw = await readFile(path, 'utf8');
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export async function writeJsonAtomic(path, value, opts = {}) {
  const tmpPath = `${path}.${process.pid}.${Date.now()}.tmp`;
  const payload = `${JSON.stringify(value, null, 2)}\n`;

  await ensureDir(dirname(path));

  try {
    await writeFile(tmpPath, payload);
    if (typeof opts.mode === 'number') {
      await chmod(tmpPath, opts.mode);
    }
    await rename(tmpPath, path);
  } catch (error) {
    try {
      await unlink(tmpPath);
    } catch {
      // ignore cleanup failure
    }
    throw error;
  }
}

export async function writeTextAtomic(path, value, opts = {}) {
  const tmpPath = `${path}.${process.pid}.${Date.now()}.tmp`;

  await ensureDir(dirname(path));

  try {
    await writeFile(tmpPath, value);
    if (typeof opts.mode === 'number') {
      await chmod(tmpPath, opts.mode);
    }
    await rename(tmpPath, path);
  } catch (error) {
    try {
      await unlink(tmpPath);
    } catch {
      // ignore cleanup failure
    }
    throw error;
  }
}

export async function removeFileIfExists(path) {
  try {
    await unlink(path);
  } catch {
    // ignore missing file
  }
}

export async function removePathIfExists(path) {
  try {
    await rm(path, { recursive: true, force: true });
  } catch {
    // ignore missing file
  }
}
