from agentrecall.compressor import MemoryCompressor

def test_compress_reduces_count():
    c = MemoryCompressor()
    texts = [
        "User lives in Marbella",
        "User's address is Autovia del Mediterraneo",
        "User has apartment 27 in Edificio Panorama",
        "User is in Malaga 29603",
    ]
    result = c.compress(texts)
    assert len(result) < len(texts)
    assert any("Marbella" in r for r in result)  # Key info preserved

def test_compress_small_list_unchanged():
    c = MemoryCompressor()
    texts = ["Fact one", "Fact two"]
    result = c.compress(texts)
    assert result == texts

def test_compress_single_text():
    c = MemoryCompressor()
    result = c.compress(["Only one text"])
    assert result == ["Only one text"]
