import numpy as np
from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
    return _model

def embed(text: str) -> np.ndarray:
    """返回 numpy 数组（用于搜索时的向量计算）"""
    model = get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.astype(np.float32)

def embed_to_bytes(text: str) -> bytes:
    """返回字节数据（用于存储到 SQLite BLOB）"""
    return embed(text).tobytes()

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))

def vec_from_bytes(data: bytes) -> np.ndarray:
    """从 SQLite BLOB 还原为 numpy 数组"""
    return np.frombuffer(data, dtype=np.float32)
