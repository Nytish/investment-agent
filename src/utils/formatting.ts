// ============================================================
// Formatting utilities — shared CLI output helpers
// ============================================================

import chalk from "chalk";

/**
 * Format a EUR amount with German locale.
 * Example: formatEur(1234.5) → "€1.234,50"
 */
export function formatEur(amount: number): string {
  return "€" + amount.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Format a percentage with optional sign prefix.
 * Example: formatPct(7.3) → "+7.3%" | formatPct(-3.1) → "-3.1%"
 */
export function formatPct(pct: number, showSign = true): string {
  const sign = showSign && pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

/**
 * Traffic-light color for a numeric value.
 * Green if positive, red if negative, yellow if zero.
 * Pass optional display text; defaults to the number as string.
 */
export function colorAmount(amount: number, text?: string): string {
  const display = text ?? String(amount);
  if (amount > 0) return chalk.green(display);
  if (amount < 0) return chalk.red(display);
  return chalk.yellow(display);
}

/**
 * Print a section divider with a centred title.
 */
export function printDivider(title: string): void {
  const line = "─".repeat(56);
  console.log(`\n${chalk.bold.blue(`── ${title} ${line.slice(title.length + 4)}`)}`);
}

/**
 * Print a key-value table row.
 * Key is left-padded to 22 characters for alignment.
 */
export function printRow(key: string, value: string): void {
  console.log(`  ${key.padEnd(22)}${value}`);
}

/** Print a green success banner. */
export function printSuccess(msg: string): void {
  console.log(chalk.green(`\n✓ ${msg}\n`));
}

/** Print a yellow warning banner. */
export function printWarning(msg: string): void {
  console.log(chalk.yellow(`\n⚠ ${msg}\n`));
}

/** Print a red error banner. */
export function printError(msg: string): void {
  console.log(chalk.red(`\n✗ ${msg}\n`));
}

/**
 * Format a notification for terminal display.
 * Returns a single multi-line string ready for console.log.
 */
export function formatNotification(type: string, title: string, body: string): string {
  const icon =
    type === "alert" ? chalk.red("🔔") :
    type === "warning" ? chalk.yellow("⚠") :
    type === "success" ? chalk.green("✓") :
    chalk.cyan("ℹ");
  return `${icon} ${chalk.bold(title)}\n   ${chalk.gray(body)}`;
}
