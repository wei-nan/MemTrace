/**
 * ts_parser.js — TypeScript / JavaScript symbol extractor
 * P4.3-D2: Uses TypeScript compiler API for accurate AST parsing.
 *
 * Usage: node ts_parser.js <file_path>
 * Output: JSON array of { name, kind, line, endLine, doc? }
 */
const fs = require('fs');
const path = require('path');

let ts;
try {
  ts = require('typescript');
} catch {
  // Fallback: if typescript is not installed, use regex-based extraction
  ts = null;
}

// ── Regex fallback (for environments without typescript package) ──────────
function parseWithRegex(code) {
  const symbols = [];
  const patterns = [
    // export class / interface / type / enum
    /(?:export\s+)?(?:abstract\s+)?(?:class|interface|type|enum)\s+([a-zA-Z0-9_$]+)/g,
    // export function / async function
    /(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)/g,
    // export const/let/var NAME = (...) => (arrow function)
    /(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s+)?\(/g,
    // export const/let/var NAME = function
    /(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s+)?function/g,
  ];

  const seen = new Set();
  for (const regex of patterns) {
    let match;
    while ((match = regex.exec(code)) !== null) {
      const name = match[1];
      if (seen.has(name)) continue;
      seen.add(name);
      const line = code.substring(0, match.index).split('\n').length;
      symbols.push({ name, kind: 'symbol', line, endLine: line + 10 });
    }
  }
  return symbols;
}

// ── TypeScript AST parsing ───────────────────────────────────────────────
function parseWithTS(code, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const isJSX = ext === '.tsx' || ext === '.jsx';
  const isTSX = ext === '.tsx' || ext === '.ts';

  const sourceFile = ts.createSourceFile(
    filePath,
    code,
    ts.ScriptTarget.Latest,
    true,  // setParentNodes
    isJSX ? ts.ScriptKind.TSX : (isTSX ? ts.ScriptKind.TS : ts.ScriptKind.JS)
  );

  const symbols = [];

  function getDoc(node) {
    const jsDocs = ts.getJSDocCommentsAndTags?.(node) || [];
    if (jsDocs.length > 0 && jsDocs[0].comment) {
      const c = jsDocs[0].comment;
      return typeof c === 'string' ? c : c.map(p => p.text || '').join('');
    }
    return undefined;
  }

  function getLineAndEnd(node) {
    const start = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
    const end = sourceFile.getLineAndCharacterOfPosition(node.getEnd());
    return { line: start.line + 1, endLine: end.line + 1 };
  }

  function visit(node, parentName) {
    const pos = getLineAndEnd(node);

    // ─ Class Declaration ─────────────────────────────────────────────
    if (ts.isClassDeclaration(node) && node.name) {
      const name = node.name.text;
      const heritage = [];
      if (node.heritageClauses) {
        for (const clause of node.heritageClauses) {
          for (const type of clause.types) {
            heritage.push(type.expression.getText(sourceFile));
          }
        }
      }
      symbols.push({
        name,
        kind: 'class',
        ...pos,
        doc: getDoc(node),
        extends: heritage.length > 0 ? heritage : undefined,
      });
      // Visit class members
      node.members.forEach(m => visit(m, name));
      return; // don't recurse further
    }

    // ─ Interface Declaration ─────────────────────────────────────────
    if (ts.isInterfaceDeclaration(node) && node.name) {
      symbols.push({
        name: node.name.text,
        kind: 'interface',
        ...pos,
        doc: getDoc(node),
      });
      return;
    }

    // ─ Type Alias Declaration ────────────────────────────────────────
    if (ts.isTypeAliasDeclaration(node) && node.name) {
      symbols.push({
        name: node.name.text,
        kind: 'type',
        ...pos,
        doc: getDoc(node),
      });
      return;
    }

    // ─ Enum Declaration ──────────────────────────────────────────────
    if (ts.isEnumDeclaration(node) && node.name) {
      symbols.push({
        name: node.name.text,
        kind: 'enum',
        ...pos,
        doc: getDoc(node),
      });
      return;
    }

    // ─ Function Declaration ──────────────────────────────────────────
    if (ts.isFunctionDeclaration(node) && node.name) {
      symbols.push({
        name: node.name.text,
        kind: 'function',
        ...pos,
        doc: getDoc(node),
        parent: parentName,
      });
      return;
    }

    // ─ Method Declaration (inside class) ─────────────────────────────
    if (ts.isMethodDeclaration(node) && node.name) {
      const name = node.name.getText(sourceFile);
      // Skip constructor and private methods starting with _
      if (name !== 'constructor') {
        symbols.push({
          name: parentName ? `${parentName}.${name}` : name,
          kind: 'method',
          ...pos,
          doc: getDoc(node),
          parent: parentName,
        });
      }
      return;
    }

    // ─ Variable Statement → Arrow functions / const exports ──────────
    if (ts.isVariableStatement(node)) {
      for (const decl of node.declarationList.declarations) {
        if (!ts.isIdentifier(decl.name)) continue;
        const name = decl.name.text;
        const init = decl.initializer;
        
        let kind = 'variable';
        if (init) {
          if (ts.isArrowFunction(init) || ts.isFunctionExpression(init)) {
            kind = 'function';
          } else if (ts.isCallExpression(init)) {
            // React.memo(...), forwardRef(...), etc.
            kind = 'component';
          }
        }
        
        // Only export top-level meaningful symbols
        if (kind !== 'variable' || (node.modifiers && node.modifiers.some(m => m.kind === ts.SyntaxKind.ExportKeyword))) {
          symbols.push({
            name,
            kind,
            ...getLineAndEnd(decl),
            doc: getDoc(node),
          });
        }
      }
      return;
    }

    // ─ Export default ─────────────────────────────────────────────────
    if (ts.isExportAssignment(node)) {
      symbols.push({
        name: 'default',
        kind: 'export',
        ...pos,
      });
      return;
    }

    // Recurse into children
    ts.forEachChild(node, child => visit(child, parentName));
  }

  visit(sourceFile, undefined);
  return symbols;
}

// ── Main ─────────────────────────────────────────────────────────────────
const file = process.argv[2];
if (!file || !fs.existsSync(file)) {
  console.log('[]');
  process.exit(0);
}

const content = fs.readFileSync(file, 'utf8');

if (ts) {
  try {
    console.log(JSON.stringify(parseWithTS(content, file)));
  } catch (e) {
    // If TS parsing fails, fall back to regex
    console.error('[ts_parser] AST parse failed, falling back to regex:', e.message);
    console.log(JSON.stringify(parseWithRegex(content)));
  }
} else {
  console.log(JSON.stringify(parseWithRegex(content)));
}
