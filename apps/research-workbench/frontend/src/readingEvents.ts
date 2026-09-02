export type ReadingMessageKind = "assistant" | "user" | "system";

export interface ReadingMessage {
  id: string;
  kind: ReadingMessageKind;
  text: string;
  streaming?: boolean;
}

export interface ReadingApproval {
  approval_id: string;
  rpc_id?: number | string;
  method: string;
  thread_id?: string;
  params: Record<string, unknown>;
}

export interface ReadingConversationState {
  messages: ReadingMessage[];
  approvals: ReadingApproval[];
  running: boolean;
}

export interface ReadingEvent {
  method?: string;
  params?: Record<string, any>;
}

export const emptyReadingConversation = (): ReadingConversationState => ({
  messages: [],
  approvals: [],
  running: false,
});

function messageId(params: Record<string, any>): string {
  return `assistant-${params.itemId || params.item?.id || params.turnId || "active"}`;
}

function finalAgentText(params: Record<string, any>): string {
  const item = params.item;
  if (!item || item.type !== "agentMessage") return "";
  if (typeof item.text === "string") return item.text;
  if (!Array.isArray(item.content)) return "";
  return item.content
    .map((part: any) => typeof part?.text === "string" ? part.text : "")
    .join("");
}

function replaceMessage(
  messages: ReadingMessage[],
  id: string,
  update: (message?: ReadingMessage) => ReadingMessage,
): ReadingMessage[] {
  const index = messages.findIndex((message) => message.id === id);
  if (index < 0) return [...messages, update()];
  const next = [...messages];
  next[index] = update(messages[index]);
  return next;
}

export function addReadingMessage(
  state: ReadingConversationState,
  message: ReadingMessage,
): ReadingConversationState {
  return { ...state, messages: [...state.messages, message] };
}

export function applyReadingEvent(
  state: ReadingConversationState,
  event: ReadingEvent,
): ReadingConversationState {
  const method = event.method || "";
  const params = event.params || {};

  if (method === "turn/started") return { ...state, running: true };
  if (method === "turn/completed") return { ...state, running: false };

  if (method === "item/agentMessage/delta" && typeof params.delta === "string") {
    const id = messageId(params);
    return {
      ...state,
      running: true,
      messages: replaceMessage(state.messages, id, (existing) => ({
        id,
        kind: "assistant",
        text: `${existing?.text || ""}${params.delta}`,
        streaming: true,
      })),
    };
  }

  if (method === "item/completed") {
    const text = finalAgentText(params);
    if (!text) return state;
    const id = messageId(params);
    return {
      ...state,
      messages: replaceMessage(state.messages, id, () => ({
        id,
        kind: "assistant",
        text,
        streaming: false,
      })),
    };
  }

  if (method === "workbench/approval-required") {
    const approval = params as ReadingApproval;
    if (!approval.approval_id) return state;
    const approvals = state.approvals.filter((item) => item.approval_id !== approval.approval_id);
    return { ...state, approvals: [...approvals, approval] };
  }

  if (method === "workbench/approval-answered") {
    const approvalId = String(params.approval_id || "");
    return { ...state, approvals: state.approvals.filter((item) => item.approval_id !== approvalId) };
  }

  if (method === "serverRequest/resolved") {
    const requestId = String(params.requestId || "");
    return {
      ...state,
      approvals: state.approvals.filter((item) => String(item.rpc_id || "") !== requestId),
    };
  }

  if (method === "workbench/error") {
    const text = String(params.detail || "Codex could not finish this step.");
    const id = `error-${params.turnId || text}`;
    return {
      ...state,
      running: false,
      messages: replaceMessage(state.messages, id, () => ({ id, kind: "system", text })),
    };
  }

  return state;
}

export function approvalDecisions(approval: ReadingApproval): string[] {
  const raw = approval.params.availableDecisions;
  if (!Array.isArray(raw)) return ["accept", "decline"];
  return raw.map((decision) => {
    if (typeof decision === "string") return decision;
    if (decision && typeof decision === "object") return String(Object.keys(decision)[0] || "");
    return "";
  }).filter(Boolean);
}

export function approvalTechnicalDetail(approval: ReadingApproval): string {
  const params = approval.params;
  const command = params.command;
  if (Array.isArray(command)) return command.join(" ");
  if (typeof command === "string") return command;
  if (typeof params.reason === "string") return params.reason;
  return "";
}
