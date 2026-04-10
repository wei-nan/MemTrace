import { Command }  from "commander";
import chalk        from "chalk";
import { listNodes, listEdges } from "../store";

export function cmdList(): Command {
  return new Command("list")
    .description("List memory nodes (and optionally edges)")
    .option("-e, --edges", "Also list edges")
    .option("-t, --type <type>", "Filter by content type")
    .option("-v, --visibility <v>", "Filter by visibility")
    .option("--tag <tag>", "Filter by tag")
    .action((opts) => {
      const nodes = listNodes().filter(n => {
        if (opts.type       && n.content.type !== opts.type)             return false;
        if (opts.visibility && n.visibility   !== opts.visibility)        return false;
        if (opts.tag        && !n.tags.includes(opts.tag))               return false;
        return true;
      });

      if (nodes.length === 0) {
        console.log(chalk.dim("No memory nodes found."));
      } else {
        console.log(chalk.cyan(`\n✦ Memory Nodes (${nodes.length})\n`));
        nodes.forEach(n => {
          const trustColor = n.trust.score >= 0.7 ? chalk.green
            : n.trust.score >= 0.4 ? chalk.yellow : chalk.red;
          console.log(
            `  ${chalk.bold(n.id)}  ${chalk.dim(n.content.type.padEnd(12))}` +
            `  trust:${trustColor(n.trust.score.toFixed(2))}` +
            `  vis:${chalk.dim(n.visibility)}\n` +
            `    ${chalk.white(n.title.en)}\n` +
            (n.tags.length ? `    ${n.tags.map(t => chalk.dim(`#${t}`)).join(" ")}\n` : "")
          );
        });
      }

      if (opts.edges) {
        const edges = listEdges();
        if (edges.length === 0) {
          console.log(chalk.dim("No edges found."));
        } else {
          console.log(chalk.cyan(`✦ Edges (${edges.length})\n`));
          edges.forEach(e => {
            const weightColor = e.weight >= 0.7 ? chalk.green
              : e.weight >= 0.4 ? chalk.yellow : chalk.red;
            console.log(
              `  ${chalk.bold(e.id)}  ${e.from}  —[${chalk.cyan(e.relation)}]→  ${e.to}` +
              `  w:${weightColor(e.weight.toFixed(3))}`
            );
          });
          console.log();
        }
      }
    });
}
