import { Command }  from "commander";
import chalk        from "chalk";
import fs           from "fs";
import path         from "path";
import { listNodes, listEdges } from "../store";

export function cmdExport(): Command {
  return new Command("export")
    .description("Export nodes (and edges) to a JSON file")
    .argument("[output]", "Output file path", `memtrace-export-${Date.now()}.json`)
    .option("--edges", "Include edges in the export")
    .option("--tag <tag>", "Only export nodes with this tag")
    .action((output: string, opts) => {
      let nodes = listNodes();
      if (opts.tag) nodes = nodes.filter(n => n.tags.includes(opts.tag));

      const nodeIds = new Set(nodes.map(n => n.id));
      const edges = opts.edges
        ? listEdges().filter(e => nodeIds.has(e.from) && nodeIds.has(e.to))
        : [];

      const payload = { schema_version: "1.0", nodes, edges };
      const outPath = path.resolve(output);

      fs.writeFileSync(outPath, JSON.stringify(payload, null, 2));

      console.log(chalk.green(`\n✓ Exported ${nodes.length} node(s)` +
        (opts.edges ? `, ${edges.length} edge(s)` : "") +
        ` → ${outPath}`));
    });
}
