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
    assert.equal(memory.skipped, false);
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
    assert.equal(skipped?.skipped, true);
    store.unskip(memory.id);
    const unskipped = store.get(memory.id);
    assert.equal(unskipped?.skipped, false);
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

describe("Confidence Decay", () => {
  it("should decay confidence on recall and delete low-confidence memories", async () => {
    const TEST_DB2 = path.join(
      os.tmpdir(),
      `agentrecall-decay-test-${Date.now()}.db`
    );
    const s = new MemoryStore({
      dbPath: TEST_DB2,
      decay_rate: 0.5,
      min_confidence: 0.3,
    });

    // Insert a memory with known starting confidence (1.0)
    const mem = await s.remember("Decay test memory", { agent: "decay" });
    assert.equal(mem.confidence, 1.0);

    // First recall: confidence should decay from 1.0 to 1.0 * (1 - 0.5) = 0.5
    await s.recall("decay", { agent: "decay" });
    const afterFirst = s.get(mem.id);
    assert.ok(afterFirst, "memory should still exist after first decay");
    assert.ok(
      Math.abs(afterFirst!.confidence - 0.5) < 0.01,
      `confidence should be ~0.5, got ${afterFirst!.confidence}`
    );

    // Second recall: confidence should decay from 0.5 to 0.5 * (1 - 0.5) = 0.25
    // 0.25 < min_confidence (0.3), so it should be deleted
    await s.recall("decay", { agent: "decay" });
    const afterSecond = s.get(mem.id);
    assert.equal(
      afterSecond,
      undefined,
      "memory should be deleted after confidence drops below min"
    );

    s.wipe();
    s.close();
  });
});

describe("Importance Scoring", () => {
  it("should rank high importance memories above low importance", async () => {
    const TEST_DB3 = path.join(
      os.tmpdir(),
      `agentrecall-importance-test-${Date.now()}.db`
    );
    const s = new MemoryStore({ dbPath: TEST_DB3 });

    // Insert both with same content prefix to match recall query
    const high = await s.remember("High priority item", {
      agent: "importance",
      importance: "high",
    });
    const low = await s.remember("Low priority item", {
      agent: "importance",
      importance: "low",
    });

    const results = await s.recall("priority item", {
      agent: "importance",
      limit: 2,
    });
    assert.ok(results.length >= 2, "should return at least 2 results");

    // High importance memory should have higher score
    const highResult = results.find((r) => r.id === high.id);
    const lowResult = results.find((r) => r.id === low.id);
    assert.ok(highResult, "high importance result should be present");
    assert.ok(lowResult, "low importance result should be present");
    assert.ok(
      highResult!.score > lowResult!.score,
      `high score (${highResult!.score}) should be > low score (${lowResult!.score})`
    );

    s.wipe();
    s.close();
  });
});

describe("Error Handling", () => {
  it("should throw on empty content", async () => {
    const TEST_DB4 = path.join(
      os.tmpdir(),
      `agentrecall-error-test-${Date.now()}.db`
    );
    const s = new MemoryStore({ dbPath: TEST_DB4 });
    await assert.rejects(
      () => s.remember(""),
      { message: "Content cannot be empty" }
    );
    await assert.rejects(
      () => s.remember("   "),
      { message: "Content cannot be empty" }
    );
    s.wipe();
    s.close();
  });

  it("should throw on operations after close", async () => {
    const TEST_DB5 = path.join(
      os.tmpdir(),
      `agentrecall-closed-test-${Date.now()}.db`
    );
    const s = new MemoryStore({ dbPath: TEST_DB5 });
    s.close();
    assert.throws(
      () => s.get(1),
      { message: "Store is closed" }
    );
  });
});
