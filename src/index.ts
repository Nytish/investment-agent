// ============================================================
// Investment Agent CLI — entry point
// Run: npm start
// ============================================================

import * as readline from "readline";
import * as fs from "fs";
import * as path from "path";
import * as dotenv from "dotenv";
import chalk from "chalk";
import ora from "ora";
import { InvestmentAgent } from "./agent/InvestmentAgent";
import { initFirebase, getUserProfile, saveUserProfile } from "./services/FirestoreService";
import { NITISH_PROFILE, NITISH_UID, DEFAULT_NOTIFICATION_SETTINGS } from "./services/SeedData";
import {
  formatEur,
  printDivider,
  printRow,
} from "./utils/formatting";

dotenv.config();

// Suppress unused-import warning for DEFAULT_NOTIFICATION_SETTINGS
void DEFAULT_NOTIFICATION_SETTINGS;

const SESSION_FILE = path.join(process.cwd(), ".session");

const BANNER = `
${chalk.bold.green("╔══════════════════════════════════════════════════════╗")}
${chalk.bold.green("║")}  ${chalk.bold.white("AI Investment Co-pilot")}  ${chalk.gray("│")}  ${chalk.cyan("Personal · EU-aware · Honest")}  ${chalk.bold.green("║")}
${chalk.bold.green("║")}  ${chalk.gray("Firebase + Gemini 2.5 Flash")}                          ${chalk.bold.green("║")}
${chalk.bold.green("╚══════════════════════════════════════════════════════╝")}
${chalk.gray("Type your question. 'exit' to quit. 'reset' for new session.")}
`;

const COMMANDS = {
  exit:      ["exit", "quit", "bye", ":q"],
  reset:     ["reset", "new session", "restart"],
  help:      ["help", "?", ":h"],
  status:    ["status", "my profile", "profile"],
  gaps:      ["gaps", "gap analysis", "check gaps"],
  portfolio: ["portfolio", "my holdings", "show portfolio"],
  insight:   ["insight", "weekly insight", "this week"],
  notify:    ["notifications", "alerts"],
  tax:       ["tax", "vorabpauschale", "tax corner"],
};

// ---------------------------------------------------------------------------
// Session persistence helpers
// ---------------------------------------------------------------------------

function loadSavedSessionId(): string | null {
  try {
    if (fs.existsSync(SESSION_FILE)) {
      const id = fs.readFileSync(SESSION_FILE, "utf8").trim();
      return id || null;
    }
  } catch {
    // ignore read errors
  }
  return null;
}

function saveSessionId(sessionId: string): void {
  try {
    fs.writeFileSync(SESSION_FILE, sessionId, "utf8");
  } catch {
    // fire-and-forget — silently ignore write failures
  }
}

// ---------------------------------------------------------------------------
// Firestore seed
// ---------------------------------------------------------------------------

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
  } catch {
    spinner.warn(chalk.yellow("Firestore unavailable — running with local profile data"));
    // Agent will use NITISH_PROFILE fallback from SeedData
  }
}

// ---------------------------------------------------------------------------
// Built-in command handlers
// ---------------------------------------------------------------------------

function printHelp(): void {
  console.log(`
${chalk.bold("Available commands:")}
  ${chalk.cyan("status")}       — Show your financial snapshot
  ${chalk.cyan("portfolio")}    — Show your current holdings
  ${chalk.cyan("gaps")}         — Run gap analysis
  ${chalk.cyan("insight")}      — Get your weekly investment insight
  ${chalk.cyan("notifications")}— Show recent alerts
  ${chalk.cyan("tax")}          — German tax obligations overview
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

  // Emergency fund colour: green >6 months, yellow 3-6, red <3
  const efMonths = p.emergencyFundMonths.toFixed(1) + " months";
  const efColored =
    p.emergencyFundMonths > 6
      ? chalk.green(efMonths)
      : p.emergencyFundMonths >= 3
      ? chalk.yellow(efMonths)
      : chalk.red(efMonths);

  // Readiness score colour: green >70, yellow 40-70, red <40
  const rsText = p.readinessScore + "/100";
  const rsColored =
    p.readinessScore > 70
      ? chalk.bold.green(rsText)
      : p.readinessScore >= 40
      ? chalk.bold.yellow(rsText)
      : chalk.bold.red(rsText);

  printDivider("Your Financial Snapshot");
  printRow("Monthly surplus", chalk.green(formatEur(p.monthlySurplus)));
  printRow("Total net worth", chalk.green(formatEur(p.netWorth)));
  printRow("Liquid assets", chalk.green(formatEur(p.liquidAssets)));
  printRow("Emergency fund", efColored);
  printRow("FIRE target", chalk.cyan(formatEur(p.fireNumber) + " by age " + p.fireTargetAge));
  printRow("Readiness score", rsColored);
  console.log(chalk.bold.blue("─".repeat(58)));
  console.log();
}

function printPortfolioSummary(): void {
  printDivider("Your Portfolio");
  printRow("EUWAX Gold II", chalk.green(formatEur(4712)));
  console.log();
  console.log(
    chalk.gray("  No other holdings tracked yet. Say 'add holding' to track investments.")
  );
  console.log(chalk.bold.blue("─".repeat(58)));
  console.log();
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

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

  // Session persistence — resume existing session if available
  const savedSessionId = loadSavedSessionId();

  const agent = new InvestmentAgent();
  agent.startSession();

  if (savedSessionId) {
    console.log(chalk.gray("  Resuming session " + savedSessionId));
  }

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

    // ── Built-in commands ──────────────────────────────────────

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

    if (COMMANDS.portfolio.includes(lower)) {
      printPortfolioSummary();
      rl.prompt();
      return;
    }

    // Commands that delegate to the AI agent
    let agentInput = input;

    if (COMMANDS.gaps.includes(lower)) {
      agentInput = input; // pass through as-is (existing behaviour)
    } else if (COMMANDS.insight.includes(lower)) {
      agentInput = "Generate my weekly investment insight";
    } else if (COMMANDS.notify.includes(lower)) {
      agentInput = "Show my recent notifications";
    } else if (COMMANDS.tax.includes(lower)) {
      agentInput = "What are my German tax obligations this year?";
    }

    // ── Send to Gemini agent ───────────────────────────────────

    const spinner = ora({
      text: chalk.gray("Thinking..."),
      spinner: "dots",
      color: "cyan"
    }).start();

    try {
      const response = await agent.chat_message(agentInput);

      spinner.stop();

      if (response.toolsUsed.length > 0) {
        console.log(chalk.gray(`  [tools: ${response.toolsUsed.join(", ")}]`));
      }

      console.log(`\n${chalk.bold.cyan("[Agent]")}\n`);
      console.log(response.text);
      console.log();

      // Persist session id (fire-and-forget)
      const sessionId = agent.getSessionId?.() ?? savedSessionId;
      if (sessionId) {
        saveSessionId(sessionId);
      }
    } catch (err) {
      spinner.stop();
      const error = err as Error;

      if (error.message.includes("FIRESTORE_OFFLINE")) {
        console.error(chalk.red(`\n[Error] ${error.message}`));
        console.log(chalk.gray("  (Firestore offline — response uses local data)"));
      } else if (error.message.includes("429")) {
        console.error(chalk.red(`\n[Error] ${error.message}`));
        console.log(chalk.yellow("  Rate limit hit. Wait 30 seconds and try again."));
      } else if (error.message.includes("API_KEY")) {
        console.error(chalk.red(`\n[Error] ${error.message}`));
        console.log(chalk.yellow("  Check your GEMINI_API_KEY in .env file."));
      } else {
        console.error(chalk.red(`\n[Error] ${error.message}\n`));
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
