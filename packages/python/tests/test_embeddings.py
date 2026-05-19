from agentrecall.embeddings import EmbeddingEngine

def test_embed_produces_vector():
    engine = EmbeddingEngine()
    vec = engine.embed("User lives in Marbella")
    assert isinstance(vec, list)
    assert len(vec) == 384  # all-MiniLM-L6-v2 dimension

def test_similarity():
    engine = EmbeddingEngine()
    v1 = engine.embed("User lives in Marbella")
    v2 = engine.embed("Where does the user live?")
    v3 = engine.embed("What is the capital of France?")
    sim_related = engine.similarity(v1, v2)
    sim_unrelated = engine.similarity(v1, v3)
    assert sim_related > sim_unrelated

def test_embed_batch():
    engine = EmbeddingEngine()
    vecs = engine.embed_batch(["hello", "world"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384
