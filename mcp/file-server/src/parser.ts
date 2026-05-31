/**
 * Tree-sitter based file parser.
 * Extracts symbol tables (functions, classes, methods) from source files.
 * Falls back to regex-based extraction for unsupported file types.
 */

import { readFileSync } from "fs";
import { extname } from "path";

export interface Symbol {
  name: string;
  kind: "function" | "class" | "method" | "variable" | "interface" | "type";
  startLine: number;
  endLine: number;
  signature: string;
  docstring?: string;
  text: string;
}

export interface ParsedFile {
  path: string;
  language: string;
  symbols: Symbol[];
  lines: string[];
}

// Per-process parser cache (session-scoped — index once, reuse)
const parseCache = new Map<string, { mtime: number; parsed: ParsedFile }>();

let Parser: any;
let treeSitterAvailable = false;

async function ensureParser() {
  if (treeSitterAvailable !== undefined) return;
  try {
    // Dynamic import to avoid hard crash if native binding missing
    const mod = await import("tree-sitter");
    Parser = mod.default;
    treeSitterAvailable = true;
  } catch {
    treeSitterAvailable = false;
  }
}

export function parseFile(absPath: string): ParsedFile | null {
  const ext = extname(absPath);
  const supportedExts = new Set([".ts", ".tsx", ".js", ".jsx", ".py", ".mts", ".mjs"]);
  if (!supportedExts.has(ext)) return null;

  try {
    const content = readFileSync(absPath, "utf8");
    const lines = content.split("\n");
    const language = extFromLang(ext);
    const symbols = extractSymbols(content, lines, language);
    return { path: absPath, language, symbols, lines };
  } catch {
    return null;
  }
}

function extFromLang(ext: string): string {
  const map: Record<string, string> = {
    ".ts": "typescript", ".tsx": "typescript",
    ".mts": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".py": "python",
  };
  return map[ext] ?? "unknown";
}

// ── Symbol extraction (regex-based, tree-sitter upgrade path) ─────────────────

function extractSymbols(content: string, lines: string[], language: string): Symbol[] {
  if (language === "typescript" || language === "javascript") {
    return extractJSTSSymbols(content, lines);
  }
  if (language === "python") {
    return extractPythonSymbols(content, lines);
  }
  return [];
}

function extractJSTSSymbols(content: string, lines: string[]): Symbol[] {
  const symbols: Symbol[] = [];

  // Patterns: exported functions, classes, interfaces, type aliases, arrow functions
  const patterns: Array<[RegExp, Symbol["kind"]]> = [
    [/^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[\(<]/gm,          "function"],
    [/^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)/gm,                  "class"],
    [/^(?:export\s+)?interface\s+(\w+)/gm,                               "interface"],
    [/^(?:export\s+)?type\s+(\w+)\s*=/gm,                                "type"],
    [/^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(/gm,           "function"],
    [/^(?:export\s+)?(?:public|private|protected|static)?\s*(?:async\s+)?(\w+)\s*\(/gm, "method"],
  ];

  for (const [pattern, kind] of patterns) {
    let match: RegExpExecArray | null;
    pattern.lastIndex = 0;
    while ((match = pattern.exec(content)) !== null) {
      const name = match[1];
      if (!name || isKeyword(name)) continue;

      const startLine = lineOf(content, match.index) + 1;
      const endLine = findBlockEnd(lines, startLine - 1);
      const sig = lines[startLine - 1]?.trim() ?? "";
      const doc = extractJSDoc(lines, startLine - 2);
      const text = lines.slice(startLine - 1, endLine).join("\n");

      if (!symbols.some((s) => s.name === name && s.startLine === startLine)) {
        symbols.push({ name, kind, startLine, endLine, signature: sig, docstring: doc, text });
      }
    }
  }

  return symbols.sort((a, b) => a.startLine - b.startLine);
}

function extractPythonSymbols(content: string, lines: string[]): Symbol[] {
  const symbols: Symbol[] = [];

  const patterns: Array<[RegExp, Symbol["kind"]]> = [
    [/^(?:async\s+)?def\s+(\w+)\s*\(/gm, "function"],
    [/^class\s+(\w+)/gm,                  "class"],
  ];

  for (const [pattern, kind] of patterns) {
    let match: RegExpExecArray | null;
    pattern.lastIndex = 0;
    while ((match = pattern.exec(content)) !== null) {
      const name = match[1];
      if (!name) continue;
      const startLine = lineOf(content, match.index) + 1;
      const endLine = findPythonBlockEnd(lines, startLine - 1);
      const sig = lines[startLine - 1]?.trim() ?? "";
      const doc = extractPyDoc(lines, startLine);
      const text = lines.slice(startLine - 1, endLine).join("\n");
      symbols.push({ name, kind, startLine, endLine, signature: sig, docstring: doc, text });
    }
  }

  return symbols.sort((a, b) => a.startLine - b.startLine);
}

// ── Outline builder ───────────────────────────────────────────────────────────

export function getOutline(parsed: ParsedFile): string {
  if (parsed.symbols.length === 0) {
    return "(no recognized symbols — try read_range)";
  }

  return parsed.symbols
    .map((s) => {
      const loc = `L${s.startLine}-${s.endLine}`;
      const doc = s.docstring ? `  // ${s.docstring}` : "";
      return `${s.kind.padEnd(10)} ${s.name.padEnd(30)} ${loc.padEnd(12)}${doc}`;
    })
    .join("\n");
}

// ── Symbol lookup ─────────────────────────────────────────────────────────────

export function getSymbol(parsed: ParsedFile, name: string): Symbol | null {
  // Exact match first, then partial
  return (
    parsed.symbols.find((s) => s.name === name) ??
    parsed.symbols.find((s) => s.name.toLowerCase() === name.toLowerCase()) ??
    parsed.symbols.find((s) => s.name.includes(name)) ??
    null
  );
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function lineOf(content: string, index: number): number {
  return content.slice(0, index).split("\n").length - 1;
}

function isKeyword(name: string): boolean {
  const kw = new Set(["if", "for", "while", "switch", "catch", "return", "async", "await",
                       "function", "class", "const", "let", "var", "import", "export"]);
  return kw.has(name);
}

function findBlockEnd(lines: string[], startIdx: number): number {
  let depth = 0;
  let opened = false;
  for (let i = startIdx; i < lines.length; i++) {
    for (const ch of lines[i]) {
      if (ch === "{") { depth++; opened = true; }
      if (ch === "}") { depth--; }
    }
    if (opened && depth === 0) return i + 1;
    if (i - startIdx > 500) return startIdx + 1; // guard against huge blocks
  }
  return lines.length;
}

function findPythonBlockEnd(lines: string[], startIdx: number): number {
  const baseIndent = lines[startIdx]?.match(/^(\s*)/)?.[1].length ?? 0;
  for (let i = startIdx + 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim() === "") continue;
    const indent = line.match(/^(\s*)/)?.[1].length ?? 0;
    if (indent <= baseIndent && line.trim() !== "") return i;
  }
  return lines.length;
}

function extractJSDoc(lines: string[], lineIdx: number): string | undefined {
  if (lineIdx < 0) return undefined;
  const prev = lines[lineIdx]?.trim();
  if (prev?.endsWith("*/")) {
    // Walk back to find /**
    for (let i = lineIdx; i >= 0 && i >= lineIdx - 15; i--) {
      if (lines[i]?.trim().startsWith("/**")) {
        const docLines = lines.slice(i, lineIdx + 1)
          .map((l) => l.replace(/^\s*\*\s?/, "").trim())
          .filter(Boolean)
          .filter((l) => !l.startsWith("@") && l !== "/**" && l !== "*/");
        return docLines[0];
      }
    }
  }
  if (prev?.startsWith("//")) return prev.replace(/^\/\/\s*/, "");
  return undefined;
}

function extractPyDoc(lines: string[], startIdx: number): string | undefined {
  const next = lines[startIdx]?.trim();
  if (next?.startsWith('"""') || next?.startsWith("'''")) {
    const doc = next.replace(/^['"]{3}/, "").replace(/['"]{3}.*$/, "").trim();
    return doc || lines[startIdx + 1]?.trim();
  }
  return undefined;
}
