import { describe, it, before, after } from "node:test";
import assert from "node:assert";
import path from "path";
import os from "os";
import { MemoryStore } from "./index.js";

const TEST_DB = path.join(os.tmpdir(), `agentrecall-test-${Date.now()}.db`);

describe("MemoryStore", () => {
  let store: MemoryStore;

  before(() => {
    store = new MemoryStore({ dbPath: TEST_DB });
  });

  after(() => {
    store.wipe();
    store.close();
  });

  it("should store and recall a memory", async () => {
    const memory = await store.remember("User prefers dark mode", {
      agent: "test",
    });
    assert.ok(memory.id > 0);
    assert.equal(memory.content, "User prefers dark mode");
    assert.equal(memory.agent, "test");
    assert.equal(memory.skip, false);
  });

  it("should classify memories automatically", async () => {
    await store.remember("I always use VS Code", { agent: "test" });
    const result = await store.recall("code editor", { agent: "test" });
    assert.ok(result.length > 0);
  });

  it("should recall by confidence", async () => {
    await store.remember("Important fact", {
      agent: "test",
      importance: "high",
    });
    await store.remember("Minor detail", {
      agent: "test",
      importance: "low",
    });
    const result = await store.recall("fact", { agent: "test", limit: 2 });
    assert.ok(result.length > 0);
  });

  it("should skip memories", async () => {
    const memory = await store.remember("Skippable content", {
      agent: "test",
    });
    store.skip(memory.id);
    const skipped = store.get(memory.id);
    assert.equal(skipped?.skip, true);
    store.unskip(memory.id);
    const unskipped = store.get(memory.id);
    assert.equal(unskipped?.skip, false);
  });

  it("should count memories", async () => {
    const count = store.count("test");
    assert.ok(count > 0);
  });

  it("should delete a memory", async () => {
    const memory = await store.remember("Delete me", { agent: "test" });
    store.delete(memory.id);
    const deleted = store.get(memory.id);
    assert.equal(deleted, undefined);
  });

  it("should wipe all memories", async () => {
    await store.remember("Wipe test", { agent: "wipe-test" });
    store.wipe({ agent: "wipe-test" });
    const count = store.count("wipe-test");
    assert.equal(count, 0);
  });
});
