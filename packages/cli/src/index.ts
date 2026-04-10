#!/usr/bin/env node

import { Command } from "commander";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
// require core locally for validation (placeholder)

const program = new Command();
const MEMTRACE_DIR = path.join(os.homedir(), ".memtrace");

if (!fs.existsSync(MEMTRACE_DIR)) {
  fs.mkdirSync(MEMTRACE_DIR, { recursive: true });
  fs.mkdirSync(path.join(MEMTRACE_DIR, "nodes"), { recursive: true });
  fs.mkdirSync(path.join(MEMTRACE_DIR, "edges"), { recursive: true });
}

program
  .name("mem")
  .description("MemTrace CLI - Collaborative memory hub")
  .version("1.0.0");

program.command("init")
  .description("Initialize local MemTrace repository")
  .action(() => {
    console.log(`Initialized empty MemTrace repository in ${MEMTRACE_DIR}`);
  });

program.command("new")
  .description("Create a new memory node")
  .action(() => {
    // Basic stub
    const id = "mem_" + Math.random().toString(36).substr(2, 6);
    const nodeItem = {
      id,
      schema_version: "1.0",
      content: { type: "factual", body: { en: "Draft...", "zh-TW": "草稿..." } }
      // placeholders
    };
    fs.writeFileSync(path.join(MEMTRACE_DIR, "nodes", `${id}.json`), JSON.stringify(nodeItem, null, 2));
    console.log(`Created new memory: ${id}`);
  });

program.command("list")
  .description("List existing memory nodes")
  .action(() => {
    const nodesDir = path.join(MEMTRACE_DIR, "nodes");
    if (!fs.existsSync(nodesDir)) return console.log("No memories found.");
    const files = fs.readdirSync(nodesDir);
    console.log(`Found ${files.length} memory node(s):`);
    files.forEach(f => console.log(` - ${f}`));
  });

program.command("link")
  .description("Create an edge between two memories")
  .argument("<from>", "Source memory ID")
  .argument("<to>", "Target memory ID")
  .option("-r, --relation <type>", "Relation type", "related_to")
  .action((from, to, options) => {
    const id = "edge_" + Math.random().toString(36).substr(2, 6);
    const edgeItem = {
      id,
      from,
      to,
      relation: options.relation,
      weight: 0.5,
      co_access_count: 0,
      last_co_accessed: new Date().toISOString(),
      decay: { half_life_days: 30, min_weight: 0.1 }
    };
    fs.writeFileSync(path.join(MEMTRACE_DIR, "edges", `${id}.json`), JSON.stringify(edgeItem, null, 2));
    console.log(`Created link: ${id} connecting ${from} -> ${to} (${options.relation})`);
  });

program.command("push")
  .description("Push local memories to remote hub")
  .action(() => {
    console.log("Pushing dependencies to GitHub... (Not implemented in Phase 1 stub)");
  });

program.command("pull")
  .description("Pull remote memories")
  .action(() => {
    console.log("Pulling latest from hub... (Not implemented in Phase 1 stub)");
  });

program.parse();
