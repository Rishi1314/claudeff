/**
 * Session-scoped file diff tracker.
 * On first access: snapshots the file content and returns it in full.
 * On subsequent access: returns a unified diff showing what changed.
 */

export class DiffTracker {
  private snapshots = new Map<string, string>();

  diff(absPath: string, currentContent: string): string {
    const prev = this.snapshots.get(absPath);

    if (prev === undefined) {
      this.snapshots.set(absPath, currentContent);
      return `[file_diff] First access — full content (${currentContent.split("\n").length} lines):\n\n${currentContent}`;
    }

    if (prev === currentContent) {
      return "[file_diff] No changes since last access.";
    }

    this.snapshots.set(absPath, currentContent);

    const patch = unifiedDiff(prev, currentContent, absPath);
    const additions = (patch.match(/^\+[^+]/gm) ?? []).length;
    const deletions = (patch.match(/^-[^-]/gm) ?? []).length;
    return `[file_diff] +${additions} -${deletions} lines changed:\n\n${patch}`;
  }
}

function unifiedDiff(before: string, after: string, label: string): string {
  const aLines = before.split("\n");
  const bLines = after.split("\n");

  // Myers diff — simplified O(n) LCS approach for readability
  const hunks = computeHunks(aLines, bLines);

  if (hunks.length === 0) return "(no diff)";

  const header = `--- ${label} (before)\n+++ ${label} (after)`;
  const body = hunks.map(formatHunk).join("\n");
  return `${header}\n${body}`;
}

interface Hunk {
  aStart: number;
  aLines: string[];
  bStart: number;
  bLines: string[];
  context: string[];
  kind: "change" | "add" | "delete";
}

function computeHunks(aLines: string[], bLines: string[]): Hunk[] {
  // Simple LCS-based diff — good enough for session diffs
  const hunks: Hunk[] = [];
  const CONTEXT = 3;

  // Build LCS table
  const m = aLines.length;
  const n = bLines.length;

  // For large files, produce approximate diff to stay fast
  if (m + n > 4000) {
    return approximateDiff(aLines, bLines);
  }

  // Standard LCS
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (aLines[i] === bLines[j]) {
        dp[i][j] = 1 + dp[i + 1][j + 1];
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }

  // Trace back
  const ops: Array<{ op: "=" | "-" | "+"; line: string; ai: number; bi: number }> = [];
  let i = 0, j = 0;
  while (i < m && j < n) {
    if (aLines[i] === bLines[j]) {
      ops.push({ op: "=", line: aLines[i], ai: i, bi: j });
      i++; j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      ops.push({ op: "-", line: aLines[i], ai: i, bi: j });
      i++;
    } else {
      ops.push({ op: "+", line: bLines[j], ai: i, bi: j });
      j++;
    }
  }
  while (i < m) { ops.push({ op: "-", line: aLines[i], ai: i, bi: j }); i++; }
  while (j < n) { ops.push({ op: "+", line: bLines[j], ai: i, bi: j }); j++; }

  // Group into hunks with context
  const changed = ops.map((o, idx) => o.op !== "=" ? idx : -1).filter((x) => x >= 0);
  if (changed.length === 0) return [];

  // Merge nearby changes into hunks
  const ranges: Array<[number, number]> = [];
  let start = Math.max(0, changed[0] - CONTEXT);
  let end = Math.min(ops.length - 1, changed[0] + CONTEXT);

  for (let k = 1; k < changed.length; k++) {
    const next = changed[k];
    if (next - CONTEXT <= end) {
      end = Math.min(ops.length - 1, next + CONTEXT);
    } else {
      ranges.push([start, end]);
      start = Math.max(0, next - CONTEXT);
      end = Math.min(ops.length - 1, next + CONTEXT);
    }
  }
  ranges.push([start, end]);

  for (const [s, e] of ranges) {
    const slice = ops.slice(s, e + 1);
    const aStart = slice.find((o) => o.op !== "+")?.ai ?? 0;
    const bStart = slice.find((o) => o.op !== "-")?.bi ?? 0;
    const lines = slice.map((o) => (o.op === "=" ? " " + o.line : o.op + o.line));
    hunks.push({
      aStart: aStart + 1,
      bStart: bStart + 1,
      aLines: slice.filter((o) => o.op === "-").map((o) => o.line),
      bLines: slice.filter((o) => o.op === "+").map((o) => o.line),
      context: lines,
      kind: "change",
    });
  }

  return hunks;
}

function approximateDiff(aLines: string[], bLines: string[]): Hunk[] {
  // For very large files: just show first diff block
  const MAX = 200;
  let firstDiff = -1;
  for (let i = 0; i < Math.min(aLines.length, bLines.length, MAX); i++) {
    if (aLines[i] !== bLines[i]) { firstDiff = i; break; }
  }
  if (firstDiff === -1) return [];
  return [{
    aStart: firstDiff + 1,
    bStart: firstDiff + 1,
    aLines: aLines.slice(firstDiff, firstDiff + 5),
    bLines: bLines.slice(firstDiff, firstDiff + 5),
    context: ["(approximate diff — file too large for full LCS)"],
    kind: "change",
  }];
}

function formatHunk(hunk: Hunk): string {
  const aCount = hunk.context.filter((l) => !l.startsWith("+")).length;
  const bCount = hunk.context.filter((l) => !l.startsWith("-")).length;
  const header = `@@ -${hunk.aStart},${aCount} +${hunk.bStart},${bCount} @@`;
  return [header, ...hunk.context].join("\n");
}
