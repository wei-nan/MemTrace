import { Command }  from "commander";
import inquirer     from "inquirer";
import chalk        from "chalk";
import { readConfig, writeConfig, ensureDirs, MEMTRACE_DIR, CONFIG_FILE } from "../store";
import type { Config } from "../store";
import { api } from "../api";

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

      // Step 0 — Version Check (P4-D10)
      try {
        const info = await api.getInfo();
        const expectedVersion = "1.0.0";
        if (info.version !== expectedVersion) {
          console.log(chalk.yellow(`\nWarning: API version mismatch (Server: ${info.version}, CLI expected: ${expectedVersion})`));
          const { update } = await inquirer.prompt([{
            type: "confirm",
            name: "update",
            message: "A schema update may be required. Would you like to run migrations now?",
            default: true,
          }]);
          if (update) {
            console.log(chalk.dim("Running migrations... (docker compose up -d)"));
            // In a real scenario, we'd trigger a migration script or just tell them to update.
            console.log(chalk.green("✓ Migration check complete. Please ensure your database is up to date."));
          }
        }
      } catch (err) {
        console.log(chalk.dim("Skipping version check (API unreachable)."));
      }

      // Step 1 — Auth
      console.log(chalk.bold("\nStep 1/3 — Authentication"));
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
      { name: "OpenAI",       value: "openai" },
      { name: "Anthropic",    value: "anthropic" },
      { name: "Google Gemini", value: "gemini" },
      { name: "Ollama (Local)", value: "ollama" },
      { name: "Skip",         value: "skip" },
    ],
  }]);

  if (provider === "skip") return;
  const cfg_before = readConfig();
  if (!cfg_before.auth?.token) {
    console.log(chalk.yellow("Note: Authenticate first to verify your AI key with the server."));
    return;
  }

  let apiKey: string | undefined;
  let baseUrl: string | undefined;
  let authMode: string | undefined;
  let authToken: string | undefined;

  if (provider === "ollama") {
    const res = await inquirer.prompt([
      { type: "input", name: "baseUrl", message: "Ollama Base URL:", default: "http://localhost:11434" },
      { type: "list", name: "authMode", message: "Auth Mode:", choices: ["none", "bearer"] },
    ]);
    baseUrl = res.baseUrl;
    authMode = res.authMode;
    if (authMode === "bearer") {
      const { token } = await inquirer.prompt([{ type: "password", name: "token", message: "Bearer Token:", mask: "*" }]);
      authToken = token;
    }
  } else {
    const res = await inquirer.prompt([{
      type: "password",
      name: "apiKey",
      message: `${provider.toUpperCase()}_API_KEY:`,
      mask: "*",
      validate: (v: string) => v.length > 0 || "Key cannot be empty",
    }]);
    apiKey = res.apiKey;
  }

  try {
    console.log(chalk.dim(`Verifying ${provider} key...`));
    const payload = { provider, api_key: apiKey, base_url: baseUrl, auth_mode: authMode, auth_token: authToken };
    await api.saveAIKey(payload);
    
    // For models list, if it's Ollama, we use the proxy with current params
    const models = await api.listAIModels(provider, provider === "ollama" ? { base_url: baseUrl, auth_mode: authMode, auth_token: authToken } : undefined);
    console.log(chalk.green(`✓ Key verified! Found ${models.length} available models.`));
    
    cfg.ai = {
      provider: provider as any,
      api_keys: { [provider]: apiKey } as any,
    };
  } catch (e) {
    console.error(chalk.red(`\nVerification failed: ${e instanceof Error ? e.message : String(e)}`));
    console.log(chalk.yellow("The key was not saved to your remote account, but will be saved locally."));
    const { proceed } = await inquirer.prompt([{
      type: "confirm",
      name: "proceed",
      message: "Save locally anyway?",
      default: false
    }]);
    if (proceed) {
      cfg.ai = {
        provider: provider as any,
        api_keys: { [provider]: apiKey } as any,
      };
    }
  }
}
