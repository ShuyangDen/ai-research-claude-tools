import assert from "node:assert/strict";
import test from "node:test";

import {
  bootstrap,
  mutate,
  uploadPdf,
  uploadProjectImage,
} from "../src/api.ts";

test("mutations refresh a stale CSRF token once and retry", async (context) => {
  const originalFetch = globalThis.fetch;
  let serverToken = "token-a";
  const requests = [];
  globalThis.fetch = async (input, init = {}) => {
    const path = String(input);
    const headers = new Headers(init.headers);
    requests.push({ path, init, csrf: headers.get("X-Workbench-CSRF") });
    if (path === "/api/bootstrap") {
      return Response.json({ csrf_token: serverToken, week: "2026-W36" });
    }
    if (headers.get("X-Workbench-CSRF") !== serverToken) {
      return Response.json({ detail: "Missing or invalid CSRF token." }, { status: 403 });
    }
    return Response.json({ ok: true, path });
  };
  context.after(() => { globalThis.fetch = originalFetch; });

  await bootstrap();

  serverToken = "token-b";
  assert.equal((await mutate("/api/example", "POST", { value: 1 })).ok, true);

  serverToken = "token-c";
  assert.equal((await uploadPdf("doi:10.1/example", new File(["%PDF"], "paper.pdf"))).ok, true);

  serverToken = "token-d";
  assert.equal((await uploadProjectImage("welfare", new File(["image"], "note.png"))).ok, true);

  assert.equal(requests.filter(({ path }) => path === "/api/bootstrap").length, 4);
  for (const expected of ["token-b", "token-c", "token-d"]) {
    assert.equal(requests.some(({ csrf }) => csrf === expected), true);
  }
});
