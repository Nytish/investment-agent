// ============================================================
// Investment Agent CLI — entry point
// Run: npm start
// ============================================================

import * as readline from "readline";
import * as dotenv from "dotenv";
import chalk from "chalk";
import ora from "ora";
import { InvestmentAgent } from "./agent/InvestmentAgent";
import { initFirebase, getUserProfile, saveUserProfile } from "./services/FirestoreService";
import { NITISH_PROFILE, NITISH_UID, DEFAULT_NOTIFICATION_SETTINGS } from "./services/SeedData";

dotenv.config();

const BANNER = `
${chalk.bold.green("╔══════════════════════════════════════════════════════╗")}
${chalk.bold.green("║")}  ${chalk.bold.white("AI Investment Co-pilot")}  ${chalk.gray("│")}  ${chalk.cyan("Personal · EU-aware · Honest")}  ${chalk.bold.green("║")}
${chalk.bold.green("║")}  ${chalk.gray("Firebase + Gemini 2.5 Flash")}                          ${chalk.bold.green("║")}
${chalk.bold.green("╚══════════════════════════════════════════════════════╝")}
${chalk.gray("Type your question. 'exit' to quit. 'reset' for new session.")}
`;

const COMMANDS = {
  exit: ["exit", "quit", "bye", ":q"],
  reset: ["reset", "new session", "restart"],
  help: ["help", "?", ":h"],
  status: ["status", "my profile", "profile"],
  gaps: ["gaps", "gap analysis", "check gaps"]
};

async function seedIfNeeded(): Promise<void> {
  const spinner = ora("Connecting to Firestore...").start();
  try {
    const existing = await getUserProfile(NITISH_UID);
    if (!existing) {
      spinner.text = "First run — seeding your Financial DNA...";
      await saveUserProfile(NITISH_PROFILE);
      spinner.succeed(chalk.green("Financial DNA seeded to Firestore ✓"));
    } else {
      spinner.succeed(chalk.green(`Welcome back, ${existing.firstName} ✓`));
    }
  } catch (err) {
    spinner.warn(chalk.yellow("Firestore unavailable — running with local profile data"));
    // Agent will use NITISH_PROFILE fallback from SeedData
  }
}

function printHelp(): void {
  console.log(`
${chalk.bold("Available commands:")}
  ${chalk.cyan("status")}       — Show your financial snapshot
  ${chalk.cyan("gaps")}         — Run gap analysis
  ${chalk.cyan("reset")}        — Start a new conversation session
  ${chalk.cyan("exit")}         — Quit the agent

${chalk.bold("Example questions:")}
  ${chalk.gray("→")} "What should I invest this month?"
  ${chalk.gray("→")} "Am I on track for FIRE at 47?"
  ${chalk.gray("→")} "What's my Vorabpauschale for 2026?"
  ${chalk.gray("→")} "Should I rebalance my portfolio?"
  ${chalk.gray("→")} "How much house down payment can I save by 2028?"
  ${chalk.gray("→")} "Compare after-tax return of VWCE vs Tagesgeld"
  ${chalk.gray("→")} "What's the risk of my plan failing?"
`);
}

function printStatus(): void {
  const p = NITISH_PROFILE;
  console.log(`
${chalk.bold.blue("── Your Financial Snapshot ──────────────────────────────")}
  Monthly surplus    ${chalk.green("€" + p.monthlySurplus.toLocaleString("de-DE"))}
  Total net worth    ${chalk.green("€" + p.netWorth.toLocaleString("de-DE"))}
  Liquid assets      ${chalk.green("€" + p.liquidAssets.toLocaleString("de-DE"))}
  Emergency fund     ${chalk.yellow(p.emergencyFundMonths.toFixed(1) + " months")}
  FIRE target        ${chalk.cyan("€" + p.fireNumber.toLocaleString("de-DE") + " by age " + p.fireTargetAge)}
  Readiness score    ${chalk.bold(p.readinessScore + "/100")}
${chalk.bold.blue("──────────────────────────────────────────────────────────")}
`);
}

async function main(): Promise<void> {
  console.log(BANNER);

  // Init Firebase + seed data
  try {
    initFirebase();
    await seedIfNeeded();
  } catch {
    console.log(chalk.yellow("⚠ Running in offline mode (Firestore not connected)"));
    console.log(chalk.gray("  Set up Firebase credentials to enable data persistence.\n"));
  }

  const agent = new InvestmentAgent();
  agent.startSession();

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: chalk.bold.green("\n[You] > ")
  });

  console.log(chalk.gray("Type 'help' to see example questions.\n"));
  rl.prompt();

  rl.on("line", async (rawInput) => {
    const input = rawInput.trim();

    if (!input) {
      rl.prompt();
      return;
    }

    const lower = input.toLowerCase();

    // Built-in commands
    if (COMMANDS.exit.includes(lower)) {
      console.log(chalk.gray("\nGoodbye, Nitish. Stay invested. 📈\n"));
      rl.close();
      process.exit(0);
    }

    if (COMMANDS.reset.includes(lower)) {
      agent.resetSession();
      agent.startSession();
      console.log(chalk.gray("  Session reset. New conversation started.\n"));
      rl.prompt();
      return;
    }

    if (COMMANDS.help.includes(lower)) {
      printHelp();
      rl.prompt();
      return;
    }

    if (COMMANDS.status.includes(lower)) {
      printStatus();
      rl.prompt();
      return;
    }

    // Send to Gemini agent
    const spinner = ora({
      text: chalk.gray("Thinking..."),
      spinner: "dots",
      color: "cyan"
    }).start();

    try {
      const response = await agent.chat_message(input);

      spinner.stop();

      if (response.toolsUsed.length > 0) {
        console.log(chalk.gray(`  [tools: ${response.toolsUsed.join(", ")}]`));
      }

      console.log(`\n${chalk.bold.cyan("[Agent]")}\n`);
      console.log(response.text);
      console.log();
    } catch (err) {
      spinner.stop();
      const error = err as Error;
      console.error(chalk.red(`\n[Error] ${error.message}\n`));

      if (error.message.includes("API_KEY")) {
        console.log(chalk.yellow("  Check your GEMINI_API_KEY in .env file."));
      }
    }

    rl.prompt();
  });

  rl.on("close", () => {
    process.exit(0);
  });
}

main().catch((err) => {
  console.error(chalk.red("Fatal error:"), err);
  process.exit(1);
});
