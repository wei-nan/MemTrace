import { Command }  from "commander";
import inquirer     from "inquirer";
import chalk        from "chalk";
import { readConfig, writeConfig, ensureDirs, MEMTRACE_DIR, CONFIG_FILE } from "../store";
import type { Config } from "../store";

export function cmdInit(): Command {
  return new Command("init")
    .description("Initialize or update local MemTrace configuration")
    .action(async () => {
      ensureDirs();

      const existing = readConfig();
      const isReinit = Object.keys(existing).length > 0;

      if (isReinit) {
        console.log(chalk.yellow("\nConfig already exists at: ") + CONFIG_FILE);
        const { action } = await inquirer.prompt([{
          type: "list",
          name: "action",
          message: "What would you like to do?",
          choices: [
            { name: "Update AI provider settings", value: "ai" },
            { name: "Re-authenticate",             value: "auth" },
            { name: "Exit",                        value: "exit" },
          ],
        }]);
        if (action === "exit") return;
        if (action === "auth")  await stepAuth(existing);
        if (action === "ai")    await stepAI(existing);
        writeConfig(existing);
        console.log(chalk.green("\nConfig updated."));
        return;
      }

      // ── Fresh init ──────────────────────────────────────────────
      console.log(chalk.cyan("\nWelcome to MemTrace! Let\'s get you set up.\n"));

      const cfg: Config = {};

      // Step 1 — Auth
      console.log(chalk.bold("Step 1/3 — Authentication"));
      await stepAuth(cfg);

      // Step 2 — AI Provider
      console.log(chalk.bold("\nStep 2/3 — AI Provider") + chalk.dim("  (optional, Enter to skip)"));
      await stepAI(cfg);

      writeConfig(cfg);

      console.log(chalk.green("\n✓ Setup complete!"));
      console.log(`  Config saved to ${chalk.cyan(CONFIG_FILE)}`);
      console.log("\nNext steps:");
      console.log("  " + chalk.cyan("memtrace new") + "          — create a memory node");
      console.log("  " + chalk.cyan("memtrace list") + "         — list all nodes");
      console.log("  " + chalk.cyan("memtrace link") + "         — connect two nodes");
      console.log("  " + chalk.cyan("memtrace --help") + "       — show all commands\n");
    });
}

async function stepAuth(cfg: Config): Promise<void> {
  const { method } = await inquirer.prompt([{
    type: "list",
    name: "method",
    message: "Authentication",
    choices: [
      { name: "Enter an API token manually", value: "token" },
      { name: "Skip (work offline)",         value: "skip" },
    ],
  }]);

  if (method === "token") {
    const { token } = await inquirer.prompt([{
      type: "password",
      name: "token",
      message: "Paste your MemTrace token:",
      mask: "*",
    }]);
    if (token) cfg.auth = { token };
  }
}

async function stepAI(cfg: Config): Promise<void> {
  const { provider } = await inquirer.prompt([{
    type: "list",
    name: "provider",
    message: "AI Provider",
    choices: [
      { name: "OpenAI",    value: "openai" },
      { name: "Anthropic", value: "anthropic" },
      { name: "Skip",      value: "skip" },
    ],
  }]);

  if (provider === "skip") return;

  const { apiKey } = await inquirer.prompt([{
    type: "password",
    name: "apiKey",
    message: `${provider === "openai" ? "OPENAI" : "ANTHROPIC"}_API_KEY:`,
    mask: "*",
    validate: (v: string) => v.length > 0 || "Key cannot be empty",
  }]);

  cfg.ai = {
    provider,
    api_keys: { [provider]: apiKey } as Partial<Record<"openai" | "anthropic", string>>,
  };
}
