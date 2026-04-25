import { Command }  from "commander";
import inquirer     from "inquirer";
import chalk        from "chalk";
import { readConfig, writeConfig, ensureDirs, MEMTRACE_DIR, CONFIG_FILE } from "../store";
import type { Config } from "../store";

export function cmdInit(): Command {
  return new Command("init")
    .description("Initialize or update local MemTrace configuration")
    .option("--token <token>", "API Token")
    .option("--url <url>", "API Base URL")
    .action(async (opts) => {
      ensureDirs();

      if (opts.token) {
        const cfg = readConfig();
        cfg.auth = { token: opts.token };
        if (opts.url) {
          cfg.api_url = opts.url;
        }
        writeConfig(cfg);
        console.log(chalk.green("✓ Configured via flags."));
        return;
      }

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
  const cfg_before = readConfig();
  if (!cfg_before.auth?.token) {
    console.log(chalk.yellow("Note: Authenticate first to verify your AI key with the server."));
    return;
  }

  const { apiKey } = await inquirer.prompt([{
    type: "password",
    name: "apiKey",
    message: `${provider.toUpperCase()}_API_KEY:`,
    mask: "*",
    validate: (v: string) => v.length > 0 || "Key cannot be empty",
  }]);

  try {
    console.log(chalk.dim(`Verifying ${provider} key...`));
    await api.saveAIKey(provider, apiKey);
    const models = await api.listAIModels(provider);
    console.log(chalk.green(`✓ Key verified! Found ${models.length} available models.`));
    
    cfg.ai = {
      provider: provider as "openai" | "anthropic",
      api_keys: { [provider]: apiKey } as Partial<Record<"openai" | "anthropic", string>>,
    };
  } catch (e) {
    console.error(chalk.red(`\nVerification failed: ${e instanceof Error ? e.message : String(e)}`));
    console.log(chalk.yellow("The key was not saved to your remote account, but will be saved locally."));
    // Still save locally if they want, but usually better to fail fast.
    const { proceed } = await inquirer.prompt([{
      type: "confirm",
      name: "proceed",
      message: "Save locally anyway?",
      default: false
    }]);
    if (proceed) {
      cfg.ai = {
        provider: provider as "openai" | "anthropic",
        api_keys: { [provider]: apiKey } as Partial<Record<"openai" | "anthropic", string>>,
      };
    }
  }
}
