import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("mobile project workspace stays width constrained and shows Codex before the board", async () => {
  const styles = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");

  assert.match(styles, /\.project-workspace-page\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s);
  assert.match(styles, /\.project-note-input textarea\s*\{[^}]*min-width:\s*0/s);
  assert.match(styles, /\.project-chat\s*\{[^}]*grid-row:\s*1/s);
  assert.match(styles, /\.project-board\s*\{\s*grid-row:\s*2/s);
  assert.match(styles, /\.project-workspace-header \.title-actions\s*\{[^}]*flex-wrap:\s*wrap/s);
  assert.match(styles, /\.project-module-list\s*\{[^}]*scroll-snap-type:\s*x mandatory/s);
});
