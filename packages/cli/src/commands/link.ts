import { Command }    from "commander";
import inquirer       from "inquirer";
import chalk          from "chalk";
import { saveEdge, loadNode, listEdges } from "../store";
import {
  generateId,
  DEFAULT_DECAY,
  DEFAULT_TRAVERSAL_EDGE,
  type Edge,
  type RelationType,
} from "@memtrace/core";

const RELATION_CHOICES = [
  { name: "depends_on  (+0.30 boost) — source requires target to be valid", value: "depends_on" },
  { name: "extends     (+0.20 boost) — source extends or supplements target", value: "extends" },
  { name: "related_to  (+0.15 boost) — related, no clear dependency direction", value: "related_to" },
  { name: "contradicts (+0.10 boost) — source conflicts with target", value: "contradicts" },
];

export function cmdLink(): Command {
  return new Command("link")
    .description("Create an edge between two memory nodes")
    .argument("<from>", "Source node ID")
    .argument("<to>", "Target node ID")
    .option("-r, --relation <type>", "Relation type (skips prompt)")
    .option("-w, --weight <number>", "Initial weight 0.1–1.0", "1.0")
    .option("-l, --half-life <days>", "Decay half-life in days", "30")
    .action(async (from: string, to: string, opts) => {
      // Validate nodes exist
      const fromNode = loadNode(from);
      const toNode   = loadNode(to);

      if (!fromNode) { console.error(chalk.red(`Node not found: ${from}`)); process.exit(1); }
      if (!toNode)   { console.error(chalk.red(`Node not found: ${to}`));   process.exit(1); }
      if (from === to) { console.error(chalk.red("Cannot link a node to itself.")); process.exit(1); }

      // Check for duplicate
      const existing = listEdges().find(
        e => e.from_id === from && e.to_id === to && e.relation === opts.relation
      );
      if (existing && opts.relation) {
        console.error(chalk.red(`Edge already exists: ${existing.id}`));
        process.exit(1);
      }

      const relation: RelationType = opts.relation ?? (await inquirer.prompt([{
        type: "list",
        name: "relation",
        message: `Relation  "${fromNode.title.en}"  →  "${toNode.title.en}":`,
        choices: RELATION_CHOICES,
      }])).relation;

      // Duplicate check after prompt
      const dup = listEdges().find(e => e.from_id === from && e.to_id === to && e.relation === relation);
      if (dup) {
        console.error(chalk.red(`Edge already exists with this relation: ${dup.id}`));
        process.exit(1);
      }

      const weight   = Math.min(1, Math.max(0.1, parseFloat(opts.weight)));
      const halfLife = Math.max(1, parseInt(opts.halfLife ?? "30", 10));

      const edge: Edge = {
        id: generateId("edge"),
        from_id: from,
        to_id: to,
        relation,
        weight,
        co_access_count: 0,
        last_co_accessed: new Date().toISOString(),
        decay: { half_life_days: halfLife, min_weight: DEFAULT_DECAY.min_weight },
        traversal: { ...DEFAULT_TRAVERSAL_EDGE },
      };

      saveEdge(edge);
      console.log(chalk.green(`\n✓ Linked: ${chalk.bold(edge.id)}`));
      console.log(`  ${from}  —[${relation}]→  ${to}`);
    });
}
