import pytest
import agent


def test_extract_prd_block_pulls_markdown_fence():
    text = 'Sure:\n```markdown\n# PRD: Thing\n\nbody\n```\ntrailing'
    assert agent.extract_prd_block(text) == "# PRD: Thing\n\nbody"


def test_extract_prd_block_missing_raises():
    with pytest.raises(agent.DraftError):
        agent.extract_prd_block("no fence here")


def test_low_confidence_sections_detected():
    prd = "# PRD\n\n## 4. Metrics\n> LOW CONFIDENCE\nguessed\n\n## 5. Reqs\nok"
    assert agent.low_confidence_sections(prd) == ["## 4. Metrics"]


def test_token_total_sums_usage_dicts():
    u1 = {"input_tokens": 100, "output_tokens": 50}
    u2 = {"input_tokens": 200, "output_tokens": 80, "cache_read_input_tokens": 10}
    assert agent.token_total([u1, u2]) == 100 + 50 + 200 + 80 + 10
