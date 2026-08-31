import pytest
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.embedding_type import EmbeddingVector
from src.modules.memory.models import VectorRecord


class _VecRow(BaseModel):
    __tablename__ = "test_embedding_rows"
    label: Mapped[str] = mapped_column(String(20))
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(EMBEDDING_DIM), nullable=True)


def test_embedding_exposes_cosine_distance():
    assert hasattr(VectorRecord.embedding, "cosine_distance")
    expr = VectorRecord.embedding.cosine_distance([0.1] * EMBEDDING_DIM)
    assert expr is not None


@pytest.mark.asyncio
async def test_embedding_roundtrip_sqlite(db_session):
    vec = [0.1] * EMBEDDING_DIM
    row = _VecRow(label="a", embedding=vec)
    db_session.add(row)
    await db_session.flush()
    loaded = (await db_session.execute(select(_VecRow))).scalar_one()
    assert loaded.embedding == pytest.approx(vec)
