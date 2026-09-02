import assert from "node:assert/strict";
import test from "node:test";

import {
  applyReadingEvent,
  approvalDecisions,
  emptyReadingConversation,
  parseTrevorSections,
  readingConversationFromSession,
} from "../src/readingEvents.ts";

test("streamed Chinese deltas stay in one readable Codex message", () => {
  let state = emptyReadingConversation();
  for (const delta of ["样", "本", "保", "留", "。"] ) {
    state = applyReadingEvent(state, {
      method: "item/agentMessage/delta",
      params: { turnId: "turn-1", itemId: "item-1", delta },
    });
  }

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].text, "样本保留。");
  assert.equal(state.messages[0].streaming, true);
});

test("the completed agent item replaces deltas as the authoritative final text", () => {
  let state = applyReadingEvent(emptyReadingConversation(), {
    method: "item/agentMessage/delta",
    params: { turnId: "turn-1", itemId: "item-1", delta: "partial" },
  });
  state = applyReadingEvent(state, {
    method: "item/completed",
    params: { turnId: "turn-1", item: { id: "item-1", type: "agentMessage", text: "完整回复" } },
  });

  assert.equal(state.messages.length, 1);
  assert.equal(state.messages[0].text, "完整回复");
  assert.equal(state.messages[0].streaming, false);
});

test("approval replay is deduplicated and resolved requests disappear", () => {
  const event = {
    method: "workbench/approval-required",
    params: {
      approval_id: "approval-1",
      rpc_id: 17,
      method: "item/commandExecution/requestApproval",
      params: { availableDecisions: ["accept", "decline"] },
    },
  };
  let state = applyReadingEvent(emptyReadingConversation(), event);
  state = applyReadingEvent(state, event);

  assert.equal(state.approvals.length, 1);
  assert.deepEqual(approvalDecisions(state.approvals[0]), ["accept", "decline"]);

  state = applyReadingEvent(state, {
    method: "serverRequest/resolved",
    params: { requestId: 17 },
  });
  assert.equal(state.approvals.length, 0);
});

test("persisted Trevor transcript hydrates after a backend restart", () => {
  const state = readingConversationFromSession([
    { message_id: "m-1", role: "assistant", text: "完整的一段回复" },
    { message_id: "m-2", role: "user", text: "继续精读" },
  ]);
  assert.equal(state.messages.length, 2);
  assert.equal(state.messages[0].text, "完整的一段回复");
  assert.equal(state.messages[1].kind, "user");
  assert.equal(state.approvals.length, 0);
});

test("Trevor's labeled workflow becomes readable sections instead of token rows", () => {
  const sections = parseTrevorSections(
    "我会按 Trevor 的 Phase 0 进行。【当前阶段】阶段 0 · 摘要导读\n【研究问题】奖学金如何影响长期教育结果？\n【只问一个问题】你想精读还是定向粗读？",
  );
  assert.deepEqual(sections, [
    { label: "Trevor", text: "我会按 Trevor 的 Phase 0 进行。" },
    { label: "当前阶段", text: "阶段 0 · 摘要导读" },
    { label: "研究问题", text: "奖学金如何影响长期教育结果？" },
    { label: "只问一个问题", text: "你想精读还是定向粗读？" },
  ]);
});
