import { Command }  from "commander";
import chalk        from "chalk";
import { loadNode, saveNode, readConfig } from "../store";
import { generateId, computeSignature, DEFAULT_TRAVERSAL_NODE, type MemoryNode } from "@memtrace/core";

export function cmdCopyNode(): Command {
  return new Command("copy-node")
    .description("Copy a single node to another workspace (edges are not copied)")
    .argument("<node-id>", "Source node ID")
    .option("--to <workspace-id>", "Target workspace ID (local: used as a tag prefix)")
    .option("--visibility <v>", "Override visibility in target (default: private)", "private")
    .action((nodeId: string, opts) => {
      const source = loadNode(nodeId);
      if (!source) {
        console.error(chalk.red(`Node not found: ${nodeId}`));
        process.exit(1);
      }

      const cfg   = readConfig();
      const author = cfg.auth?.token ? "authenticated-user" : "local-user";
      const now    = new Date().toISOString();
      const newId  = generateId("mem");

      const copied: MemoryNode = {
        ...source,
        id: newId,
        visibility: opts.visibility as MemoryNode["visibility"],
        provenance: {
          ...source.provenance,
          author,
          created_at: now,
          updated_at: undefined,
          source_document: undefined,
          extraction_model: undefined,
          copied_from: {
            node_id: source.id,
            workspace_id: opts.to ?? cfg.default_workspace ?? "local",
          },
          signature: computeSignature({
            title:   source.title,
            content: source.content,
            tags:    source.tags,
            author,
          }),
        },
        // Trust snapshot carried over; traversal resets
        traversal: { ...DEFAULT_TRAVERSAL_NODE },
      };

      saveNode(copied);
      console.log(chalk.green(`\n✓ Copied: ${chalk.bold(newId)}`));
      console.log(`  from: ${nodeId}  →  to workspace: ${opts.to ?? "local"}`);
      console.log(chalk.dim(`  visibility: ${copied.visibility}  |  edges not copied`));
    });
}
