export function getInitialUsageCheckAt({ runtimeId, usageState, nowEpoch }) {
  if (runtimeId === 'codex') return 0;

  if (usageState?.lastCheckEpoch) return usageState.lastCheckEpoch;

  // Fresh Claude installs should still wait a full interval before the first
  // snapshot read. Codex refreshes immediately so usage-codex.json (or the
  // rollout fallback) can repopulate the persisted state after restart.

  return nowEpoch;
}
