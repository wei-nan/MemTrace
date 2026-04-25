import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { readConfig } from "../store";
import { api } from "../api";

export function cmdIngest(): Command {
  return new Command("ingest")
    .description("Ingest a document file (PDF, DOCX, MD, TXT) into a workspace")
    .argument("<file-path>", "Path to the file to ingest")
    .option("--workspace <ws-id>", "Target workspace ID")
    .action(async (filePath: string, opts) => {
      const cfg = readConfig();
      const wsId = opts.workspace || cfg.default_workspace;

      if (!wsId) {
        console.error(chalk.red("Error: Workspace ID is required. Use --workspace or set default_workspace in config."));
        process.exit(1);
      }

      if (!fs.existsSync(filePath)) {
        console.error(chalk.red(`Error: File not found: ${filePath}`));
        process.exit(1);
      }

      const token = cfg.auth?.token;
      if (!token) {
        console.error(chalk.red("Error: Authentication required. Run 'memtrace init' first."));
        process.exit(1);
      }

      try {
        console.log(chalk.cyan(`\nUploading ${path.basename(filePath)} to workspace ${wsId}...`));
        
        const API_BASE = process.env.MEMTRACE_API || "http://localhost:8000/api/v1";
        
        const form = new FormData();
        const buffer = fs.readFileSync(filePath);
        const blob = new Blob([buffer]);
        form.append("file", blob, path.basename(filePath));

        const res = await fetch(`${API_BASE}/workspaces/${wsId}/ingest`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          },
          body: form
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || res.statusText);
        }

        const data = await res.json();
        console.log(chalk.green(`\n✓ Upload successful! Job ID: ${chalk.bold(data.id || data.job_id || "pending")}`));
        console.log(chalk.dim("The document is being processed in the background."));
        console.log(`Check status with: ${chalk.cyan(`memtrace ingest-status ${wsId}`)}`);
      } catch (e) {
        console.error(chalk.red(`\nFailed to ingest file: ${e instanceof Error ? e.message : String(e)}`));
        process.exit(1);
      }
    });
}
