import fs from 'node:fs';

function parseJsonFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function formatResetTime(epochSeconds) {
  if (!epochSeconds) return null;

  try {
    const resetAt = new Date(epochSeconds * 1000);
    const now = new Date();
    const sameDay =
      resetAt.getFullYear() === now.getFullYear() &&
      resetAt.getMonth() === now.getMonth() &&
      resetAt.getDate() === now.getDate();

    const time = new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }).format(resetAt);

    if (sameDay) return time;

    const date = new Intl.DateTimeFormat('en-US', {
      day: 'numeric',
      month: 'short'
    }).format(resetAt);

    return `${time} on ${date}`;
  } catch {
    return null;
  }
}

function normalizePersistedUsage(snapshot, statusShape = 'persisted_usage') {
  if (!snapshot || typeof snapshot !== 'object') return null;

  const sessionPercent = snapshot.session?.percent;
  const weeklyAllPercent = snapshot.weeklyAll?.percent;
  const weeklySonnetPercent = snapshot.weeklySonnet?.percent;
  const fiveHourPercent = snapshot.fiveHour?.percent;

  if (
    sessionPercent == null &&
    weeklyAllPercent == null &&
    weeklySonnetPercent == null &&
    fiveHourPercent == null
  ) {
    return null;
  }

  return {
    sessionPercent: sessionPercent ?? null,
    sessionResets: snapshot.session?.resets ?? null,
    weeklyAllPercent: weeklyAllPercent ?? null,
    weeklyAllResets: snapshot.weeklyAll?.resets ?? null,
    weeklySonnetPercent: weeklySonnetPercent ?? null,
    weeklySonnetResets: snapshot.weeklySonnet?.resets ?? null,
    fiveHourPercent: fiveHourPercent ?? null,
    fiveHourResets: snapshot.fiveHour?.resets ?? null,
    statusShape
  };
}

function normalizeClaudeStatusline(status) {
  if (!status || typeof status !== 'object') return null;

  if (status.usage && typeof status.usage === 'object') {
    const normalized = normalizePersistedUsage(status.usage, 'statusline_usage');
    if (normalized) return normalized;
  }

  const rateLimits = status.rate_limits;
  if (rateLimits && typeof rateLimits === 'object') {
    const primary = rateLimits.primary;
    const secondary = rateLimits.secondary;
    const sonnet = rateLimits.sonnet;

    const sessionPercent = primary?.used_percent ?? null;
    const weeklyAllPercent = secondary?.used_percent ?? null;
    const weeklySonnetPercent = sonnet?.used_percent ?? null;

    if (
      sessionPercent != null ||
      weeklyAllPercent != null ||
      weeklySonnetPercent != null
    ) {
      return {
        sessionPercent,
        sessionResets: formatResetTime(primary?.resets_at ?? null),
        weeklyAllPercent,
        weeklyAllResets: formatResetTime(secondary?.resets_at ?? null),
        weeklySonnetPercent,
        weeklySonnetResets: formatResetTime(sonnet?.resets_at ?? null),
        fiveHourPercent: null,
        fiveHourResets: null,
        statusShape: 'statusline_rate_limits'
      };
    }

    // Format B: five_hour/seven_day keys with used_percentage (Claude Code 2.1.x+)
    const fiveHour = rateLimits.five_hour;
    const sevenDay = rateLimits.seven_day;
    const fiveHourPercent = fiveHour?.used_percentage ?? null;
    const weeklyAllPercentB = sevenDay?.used_percentage ?? null;

    if (fiveHourPercent != null || weeklyAllPercentB != null) {
      return {
        sessionPercent: status.context_window?.used_percentage ?? null,
        sessionResets: null,
        weeklyAllPercent: weeklyAllPercentB,
        weeklyAllResets: formatResetTime(sevenDay?.resets_at ?? null),
        weeklySonnetPercent: null,
        weeklySonnetResets: null,
        fiveHourPercent,
        fiveHourResets: formatResetTime(fiveHour?.resets_at ?? null),
        statusShape: 'statusline_rate_limits'
      };
    }
  }

  return normalizePersistedUsage(status, 'statusline_persisted_usage');
}

export function readClaudeUsageFromMonitorFiles({ statuslineFile, usageStateFile }) {
  const statusline = parseJsonFile(statuslineFile);
  const fromStatusline = normalizeClaudeStatusline(statusline);
  if (fromStatusline) return fromStatusline;

  const usageState = parseJsonFile(usageStateFile);
  return normalizePersistedUsage(usageState, 'usage_json');
}

export function readCodexUsageFromMonitorFile({ usageStateFile }) {
  const usageState = parseJsonFile(usageStateFile);
  return normalizePersistedUsage(usageState, 'usage_codex_json');
}
