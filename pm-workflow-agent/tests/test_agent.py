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


def test_merge_usage_sums_fields():
    merged = agent.merge_usage([
        {"input_tokens": 100, "output_tokens": 50},
        {"input_tokens": 200, "output_tokens": 80, "cache_read_input_tokens": 10},
    ])
    assert merged["input_tokens"] == 300
    assert merged["output_tokens"] == 130
    assert merged["cache_read_input_tokens"] == 10


@pytest.mark.asyncio
async def test_run_validated_retries_once(monkeypatch):
    calls = {"n": 0}

    async def fake_run(prompt, *, system, use_skill):
        calls["n"] += 1
        text = "bad" if calls["n"] == 1 else "```markdown\n# PRD: X\n```"
        return text, {"input_tokens": 10, "output_tokens": 5}

    monkeypatch.setattr(agent, "_run", fake_run)
    text, usage = await agent._run_validated(
        "p", system="s", use_skill=False, validate=agent.extract_prd_block,
    )
    assert calls["n"] == 2
    assert "# PRD: X" in text
    assert usage["input_tokens"] == 20  # both attempts merged


@pytest.mark.asyncio
async def test_run_validated_raises_after_second_failure(monkeypatch):
    async def fake_run(prompt, *, system, use_skill):
        return "still bad", {"input_tokens": 10, "output_tokens": 5}

    monkeypatch.setattr(agent, "_run", fake_run)
    with pytest.raises(agent.DraftError):
        await agent._run_validated(
            "p", system="s", use_skill=False, validate=agent.extract_prd_block,
        )
