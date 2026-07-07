from src.evaluation.evaluationConstants import evaluation_result_passes


def test_evaluation_pass_rule() -> None:
    assert evaluation_result_passes(hallucination_score=0.2, faithfulness_score=0.6) is True
    assert evaluation_result_passes(hallucination_score=0.4, faithfulness_score=0.6) is False
    assert evaluation_result_passes(hallucination_score=0.2, faithfulness_score=0.4) is False
