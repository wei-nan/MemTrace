#!/usr/bin/env node

import { Command } from "commander";
import { cmdInit }      from "./commands/init";
import { cmdNew }       from "./commands/new";
import { cmdLink }      from "./commands/link";
import { cmdList }      from "./commands/list";
import { cmdExport }    from "./commands/export";
import { cmdImport }    from "./commands/import";
import { cmdCopyNode }  from "./commands/copy-node";
import { cmdIngest }    from "./commands/ingest";
import { cmdSearch }    from "./commands/search";

const program = new Command();

program
  .name("memtrace")
  .description("MemTrace CLI — Collaborative memory hub")
  .version("1.0.0");

program.addCommand(cmdInit());
program.addCommand(cmdNew());
program.addCommand(cmdLink());
program.addCommand(cmdList());
program.addCommand(cmdExport());
program.addCommand(cmdImport());
program.addCommand(cmdCopyNode());
program.addCommand(cmdIngest());
program.addCommand(cmdSearch());

program.parse();
