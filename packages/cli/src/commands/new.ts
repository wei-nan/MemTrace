import { Command }  from "commander";
import inquirer     from "inquirer";
import chalk        from "chalk";
import { saveNode } from "../store";
import {
  generateId,
  computeSignature,
  DEFAULT_TRUST,
  DEFAULT_TRAVERSAL_NODE,
  type MemoryNode,
  type ContentType,
  type ContentFormat,
  type Visibility,
} from "@memtrace/core";
import { readConfig } from "../store";

export function cmdNew(): Command {
  return new Command("new")
    .description("Create a new memory node interactively")
    .action(async () => {
      const cfg = readConfig();
      const author = cfg.auth?.token
        ? "authenticated-user"   // replaced with real username once API is wired
        : "local-user";

      console.log(chalk.cyan("\n✦ New Memory Node\n"));

      const answers = await inquirer.prompt([
        {
          type: "input",
          name: "title_zh",
          message: "Title (zh-TW):",
          validate: (v: string) => v.trim().length > 0 || "Required",
        },
        {
          type: "input",
          name: "title_en",
          message: "Title (en):",
          validate: (v: string) => v.trim().length > 0 || "Required",
        },
        {
          type: "list",
          name: "content_type",
          message: "Content type:",
          choices: ["factual", "procedural", "preference", "context"],
        },
        {
          type: "list",
          name: "format",
          message: "Body format:",
          choices: [
            { name: "plain  — raw text", value: "plain" },
            { name: "markdown — Markdown source", value: "markdown" },
          ],
        },
        {
          type: "editor",
          name: "body_zh",
          message: "Body (zh-TW) — opens editor, save & close to continue:",
        },
        {
          type: "editor",
          name: "body_en",
          message: "Body (en) — opens editor, save & close to continue:",
        },
        {
          type: "input",
          name: "tags",
          message: "Tags (comma-separated, optional):",
        },
        {
          type: "list",
          name: "visibility",
          message: "Visibility:",
          choices: ["private", "team", "public"],
          default: "private",
        },
      ]);

      const tags: string[] = answers.tags
        ? answers.tags.split(",").map((t: string) => t.trim()).filter(Boolean)
        : [];

      const title = {
        "zh-TW": answers.title_zh.trim(),
        en: answers.title_en.trim(),
      };
      const content = {
        type: answers.content_type as ContentType,
        format: answers.format as ContentFormat,
        body: {
          "zh-TW": answers.body_zh.trim(),
          en: answers.body_en.trim(),
        },
      };

      const id = generateId("mem");
      const now = new Date().toISOString();
      const signature = computeSignature({ title, content, tags, author });

      const node: MemoryNode = {
        id,
        schema_version: "1.0",
        title,
        content,
        tags,
        visibility: answers.visibility as Visibility,
        provenance: {
          author,
          created_at: now,
          signature,
          source_type: "human",
        },
        trust: { ...DEFAULT_TRUST },
        traversal: { ...DEFAULT_TRAVERSAL_NODE },
      };

      saveNode(node);
      console.log(chalk.green(`\n✓ Created: ${chalk.bold(id)}`));
      console.log(`  "${title.en}"`);
      console.log(chalk.dim(`\n  memtrace link ${id} <other-id>  — connect to another node`));
    });
}
