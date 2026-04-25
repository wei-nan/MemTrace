import { Command }  from "commander";
import chalk        from "chalk";
import { api } from "../api";

export function cmdSearch(): Command {
  return new Command("search")
    .description("Search knowledge nodes by keyword")
    .argument("<query>", "Search keyword")
    .option("-w, --workspace <id>", "Workspace ID")
    .action(async (query: string, opts) => {
      const wsId = opts.workspace;
      if (!wsId) {
        console.error(chalk.red("Error: Workspace ID (-w) is required for search."));
        process.exit(1);
      }

      console.log(chalk.dim(`Searching for "${query}" in ${wsId}...`));

      try {
        // We need to add search to api.ts
        const results = await (api as any).searchNodes(wsId, query);
        
        if (results.length === 0) {
          console.log(chalk.yellow("No results found."));
          return;
        }

        console.log(chalk.cyan(`\n✦ Search Results (${results.length})\n`));
        results.forEach((n: any) => {
          console.log(
            `  ${chalk.bold(n.id)}  ${chalk.white(n.title_en || n.title_zh)}\n` +
            `    ${chalk.dim(n.body_en?.substring(0, 100) || n.body_zh?.substring(0, 100))}...\n`
          );
        });
      } catch (e) {
        console.error(chalk.red(`Search failed: ${e instanceof Error ? e.message : String(e)}`));
      }
    });
}
