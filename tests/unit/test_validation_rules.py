from driftwatch.validation.rules import check_claim_consistency


def test_grounded_description_passes():
    consistent, reason = check_claim_consistency(
        "User input reaches a shell command via subprocess.run(..., shell=True).",
        "The user_id parameter flows directly into the shell command.",
    )
    assert consistent is True
    assert reason is None


def test_overstated_certainty_is_flagged():
    consistent, reason = check_claim_consistency(
        "This will always cause a remote code execution vulnerability.",
        "reasoning",
    )
    assert consistent is False
    assert "will always" in reason.lower()


def test_guaranteed_language_is_flagged():
    consistent, reason = check_claim_consistency("This is guaranteed to be exploitable.", "")
    assert consistent is False
