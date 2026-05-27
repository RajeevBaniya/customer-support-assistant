from src.schemas.ragSchemas import RagAskResponse


def build_rag_payload(model: RagAskResponse) -> dict[str, object]:
    return model.model_dump(mode="json")
