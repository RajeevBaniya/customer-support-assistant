from collections.abc import Iterator, Sequence


def batch_texts(texts: Sequence[str], batch_size: int) -> Iterator[list[str]]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    batch: list[str] = []
    for item in texts:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
