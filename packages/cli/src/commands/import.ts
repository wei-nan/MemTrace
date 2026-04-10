import { Command }   from "commander";
import chalk         from "chalk";
import fs            from "fs";
import path          from "path";
import { saveNode, saveEdge, loadNode, listEdges } from "../store";
import { validateNode, validateEdge } from "@memtrace/core";

export function cmdImport(): Command {
  return new Command("import")
    .description("Import nodes and edges from a JSON export file or a directory of node files")
    .argument("<source>", "Path to a .json export file or a directory of node JSON files")
    .option("--skip-invalid", "Skip invalid records instead of aborting")
    .option("--dry-run",      "Validate and report without writing anything")
    .action((source: string, opts) => {
      const srcPath = path.resolve(source);

      let nodes: any[] = [];
      let edges: any[] = [];

      // ── Detect input format ──────────────────────────────────────
      const stat = fs.statSync(srcPath);

      if (stat.isDirectory()) {
        // Directory of individual node JSON files
        nodes = fs.readdirSync(srcPath)
          .filter(f => f.endsWith(".json"))
          .map(f => JSON.parse(fs.readFileSync(path.join(srcPath, f), "utf8")));
      } else {
        // Single export bundle  { schema_version, nodes[], edges[] }
        const raw = JSON.parse(fs.readFileSync(srcPath, "utf8"));
        if (raw.nodes)  nodes = raw.nodes;
        if (raw.edges)  edges = raw.edges;
        // Also support a flat array of nodes
        if (Array.isArray(raw)) nodes = raw;
      }

      let importedNodes = 0, skippedNodes = 0;
      let importedEdges = 0, skippedEdges = 0;

      // ── Nodes ─────────────────────────────────────────────────────
      for (const node of nodes) {
        const { valid, errors } = validateNode(node);
        if (!valid) {
          console.warn(chalk.yellow(`  ⚠ Node ${node.id ?? "?"} invalid: `) +
            errors?.map(e => e.message).join(", "));
          if (!opts.skipInvalid) { console.error(chalk.red("Aborting. Use --skip-invalid to continue.")); process.exit(1); }
          skippedNodes++;
          continue;
        }
        if (loadNode(node.id)) {
          console.log(chalk.dim(`  ~ Node ${node.id} already exists, skipping`));
          skippedNodes++;
          continue;
        }
        if (!opts.dryRun) saveNode(node);
        importedNodes++;
      }

      // ── Edges ─────────────────────────────────────────────────────
      for (const edge of edges) {
        const { valid, errors } = validateEdge(edge);
        if (!valid) {
          console.warn(chalk.yellow(`  ⚠ Edge ${edge.id ?? "?"} invalid: `) +
            errors?.map(e => e.message).join(", "));
          if (!opts.skipInvalid) { console.error(chalk.red("Aborting. Use --skip-invalid to continue.")); process.exit(1); }
          skippedEdges++;
          continue;
        }
        const dup = listEdges().find(e => e.id === edge.id);
        if (dup) { skippedEdges++; continue; }
        if (!opts.dryRun) saveEdge(edge);
        importedEdges++;
      }

      const prefix = opts.dryRun ? chalk.cyan("[dry-run] ") : "";
      console.log(chalk.green(`\n${prefix}✓ Imported ${importedNodes} node(s)` +
        (edges.length ? `, ${importedEdges} edge(s)` : "") +
        (skippedNodes + skippedEdges > 0
          ? chalk.dim(` (skipped ${skippedNodes + skippedEdges})`)
          : "")));
    });
}
