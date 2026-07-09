def test_coherence_pass_and_media_valid_are_not_enough():
    validation = {
        "transcript_valid": True,
        "selected_scope_lexical_valid": True,
        "content_coherence_valid": True,
        "task_coverage_valid": False,
        "content_sufficiency_valid": False,
        "policy_valid": True,
        "media_valid": True,
    }
    automated = all(
        validation[key]
        for key in [
            "transcript_valid",
            "selected_scope_lexical_valid",
            "content_coherence_valid",
            "task_coverage_valid",
            "content_sufficiency_valid",
            "policy_valid",
            "media_valid",
        ]
    )
    assert automated is False
