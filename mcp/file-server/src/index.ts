#!/usr/bin/env node
/**
 * claudeff file-server — Token-efficient MCP server for Claude Code.
 *
 * Exposes surgical file access tools that replace full-file reads:
 *   read_symbol   — return only a named function/class body
 *   file_outline  — signatures + docstrings, no bodies (80-95% token savings)
 *   read_range    — line range slice of a file
 *   search_symbols — find symbol definitions across files
 *   file_diff     — what changed since first access this session
 *
 * Install as MCP in ~/.claude/settings.json:
 *   "mcpServers": { "file-server": { "command": "node", "args": ["/path/to/dist/index.js"] } }
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync, existsSync } from "fs";
import { resolve, extname } from "path";
import { parseFile, getSymbol, getOutline, type ParsedFile } from "./parser.js";
import { DiffTracker } from "./diff.js";

const server = new Server(
  { name: "claudeff-file-server", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

const diffTracker = new DiffTracker();

// ── Tool definitions ──────────────────────────────────────────────────────────

const TOOLS: Tool[] = [
  {
    name: "read_symbol",
    description:
      "Return only a named symbol (function, class, method, variable) from a file. " +
      "Dramatically cheaper than reading the whole file. " +
      "Use instead of Read when you know what symbol you need.",
    inputSchema: {
      type: "object",
      properties: {
        file_path: { type: "string", description: "Absolute or relative file path" },
        symbol:    { type: "string", description: "Symbol name to find (function, class, etc.)" },
      },
      required: ["file_path", "symbol"],
    },
  },
  {
    name: "file_outline",
    description:
      "Return a structural outline of a file: all symbols with their signatures and " +
      "one-line docstrings, but NOT their bodies. " +
      "Typically 80-95% fewer tokens than reading the full file. " +
      "Use this to understand a file's API before deciding what to read_symbol.",
    inputSchema: {
      type: "object",
      properties: {
        file_path: { type: "string", description: "Absolute or relative file path" },
      },
      required: ["file_path"],
    },
  },
  {
    name: "read_range",
    description:
      "Read a specific line range from a file. " +
      "Use when you know the approximate location of what you need.",
    inputSchema: {
      type: "object",
      properties: {
        file_path:  { type: "string", description: "Absolute or relative file path" },
        start_line: { type: "number", description: "First line (1-indexed)" },
        end_line:   { type: "number", description: "Last line (1-indexed, inclusive)" },
      },
      required: ["file_path", "start_line", "end_line"],
    },
  },
  {
    name: "search_symbols",
    description:
      "Find where a symbol is defined across files. " +
      "Returns file paths and line numbers, not full source. " +
      "Use instead of Grep when looking for function/class definitions.",
    inputSchema: {
      type: "object",
      properties: {
        symbol:    { type: "string", description: "Symbol name to find" },
        directory: { type: "string", description: "Root directory to search (default: cwd)" },
        extensions: {
          type: "array",
          items: { type: "string" },
          description: "File extensions to include, e.g. [\".ts\", \".js\"] (default: all supported)",
        },
      },
      required: ["symbol"],
    },
  },
  {
    name: "file_diff",
    description:
      "Return what changed in a file since you first accessed it this session. " +
      "On first call, returns the full file and records the snapshot. " +
      "On subsequent calls, returns only the diff — use this to track your own edits cheaply.",
    inputSchema: {
      type: "object",
      properties: {
        file_path: { type: "string", description: "Absolute or relative file path" },
      },
      required: ["file_path"],
    },
  },
];

// ── Tool handlers ─────────────────────────────────────────────────────────────

function resolveFile(file_path: string): string {
  return resolve(process.cwd(), file_path);
}

function readLines(absPath: string): string[] {
  return readFileSync(absPath, "utf8").split("\n");
}

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;

  try {
    switch (name) {
      case "read_symbol": {
        const { file_path, symbol } = args as { file_path: string; symbol: string };
        const absPath = resolveFile(file_path);
        if (!existsSync(absPath)) {
          return err(`File not found: ${file_path}`);
        }
        const parsed = parseFile(absPath);
        if (!parsed) {
          return err(`Cannot parse file type: ${extname(file_path)}`);
        }
        const result = getSymbol(parsed, symbol);
        if (!result) {
          const available = parsed.symbols.map((s) => s.name).join(", ");
          return err(`Symbol '${symbol}' not found. Available: ${available || "none"}`);
        }
        return ok(
          `// ${file_path}:${result.startLine}-${result.endLine} — ${result.kind} ${result.name}\n\n` +
          result.text
        );
      }

      case "file_outline": {
        const { file_path } = args as { file_path: string };
        const absPath = resolveFile(file_path);
        if (!existsSync(absPath)) {
          return err(`File not found: ${file_path}`);
        }
        const parsed = parseFile(absPath);
        if (!parsed) {
          // Fallback: first 60 lines for unsupported types
          const lines = readLines(absPath).slice(0, 60);
          return ok(`[Unsupported type — first 60 lines]\n\n${lines.join("\n")}`);
        }
        const outline = getOutline(parsed);
        return ok(`// ${file_path} — outline (${parsed.symbols.length} symbols)\n\n${outline}`);
      }

      case "read_range": {
        const { file_path, start_line, end_line } = args as {
          file_path: string;
          start_line: number;
          end_line: number;
        };
        const absPath = resolveFile(file_path);
        if (!existsSync(absPath)) {
          return err(`File not found: ${file_path}`);
        }
        const lines = readLines(absPath);
        const slice = lines.slice(start_line - 1, end_line);
        const numbered = slice.map((l, i) => `${start_line + i}\t${l}`).join("\n");
        return ok(numbered);
      }

      case "search_symbols": {
        const { symbol, directory, extensions } = args as {
          symbol: string;
          directory?: string;
          extensions?: string[];
        };
        const root = directory ? resolve(directory) : process.cwd();
        const exts = extensions ?? [".ts", ".tsx", ".js", ".jsx", ".py"];
        const matches = await searchSymbolsInDir(root, symbol, exts);
        if (matches.length === 0) {
          return ok(`No definitions found for '${symbol}'`);
        }
        const lines = matches.map(
          (m) => `${m.file}:${m.line}  ${m.kind} ${m.name}`
        );
        return ok(`Definitions of '${symbol}':\n\n${lines.join("\n")}`);
      }

      case "file_diff": {
        const { file_path } = args as { file_path: string };
        const absPath = resolveFile(file_path);
        if (!existsSync(absPath)) {
          return err(`File not found: ${file_path}`);
        }
        const content = readFileSync(absPath, "utf8");
        const diff = diffTracker.diff(absPath, content);
        return ok(diff);
      }

      default:
        return err(`Unknown tool: ${name}`);
    }
  } catch (e) {
    return err(`Error: ${e instanceof Error ? e.message : String(e)}`);
  }
});

// ── Symbol search ─────────────────────────────────────────────────────────────

import { readdirSync, statSync } from "fs";
import { join } from "path";

interface SymbolMatch {
  file: string;
  line: number;
  kind: string;
  name: string;
}

async function searchSymbolsInDir(
  root: string,
  symbol: string,
  exts: string[],
  results: SymbolMatch[] = [],
  depth = 0
): Promise<SymbolMatch[]> {
  if (depth > 8 || results.length > 50) return results;

  let entries: string[];
  try {
    entries = readdirSync(root);
  } catch {
    return results;
  }

  const SKIP = new Set(["node_modules", ".git", "dist", "build", "__pycache__", ".next"]);

  for (const entry of entries) {
    const full = join(root, entry);
    try {
      const stat = statSync(full);
      if (stat.isDirectory()) {
        if (!SKIP.has(entry)) {
          await searchSymbolsInDir(full, symbol, exts, results, depth + 1);
        }
      } else if (exts.includes(extname(entry))) {
        const parsed = parseFile(full);
        if (parsed) {
          for (const sym of parsed.symbols) {
            if (sym.name === symbol || sym.name.includes(symbol)) {
              results.push({ file: full, line: sym.startLine, kind: sym.kind, name: sym.name });
            }
          }
        }
      }
    } catch {
      // skip unreadable files
    }
  }

  return results;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function ok(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

function err(text: string) {
  return { content: [{ type: "text" as const, text: `[error] ${text}` }], isError: true };
}

// ── Start ─────────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
