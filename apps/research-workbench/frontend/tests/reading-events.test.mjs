import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("Reading Room is an overview with three Codex handoff decisions", async () => {
  const source = await readFile(new URL("../src/App.tsx", import.meta.url), "utf8");
  const start = source.indexOf("function ReadingView");
  const end = source.indexOf("function IdeasView", start);
  const readingView = source.slice(start, end);

  assert.match(readingView, /reading-overview-layout/);
  assert.match(readingView, /onAction\(paper, "deep"\)/);
  assert.match(readingView, /onAction\(paper, "targeted"\)/);
  assert.match(readingView, /onAction\(paper, "skip"\)/);
  assert.doesNotMatch(readingView, /sessionSocket|composer|sendMessage|answerApproval|uploadPdf/);
  assert.match(readingView, /不会弹出或跳转窗口/);
  assert.match(readingView, /合法 PDF/);
});
