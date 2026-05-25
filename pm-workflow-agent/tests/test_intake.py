import pytest
import intake


def test_checklist_has_six_items():
    assert len(intake.COVERAGE_CHECKLIST) == 6
    ids = {c["id"] for c in intake.COVERAGE_CHECKLIST}
    assert ids == {"problem", "persona", "metric", "dependencies", "scope", "release"}


def test_parse_questions_from_fenced_json():
    text = '''Here are the gaps:
```json
{"questions": [
  {"id": "q1", "checklist_item": "metric", "text": "What is the top success metric?"}
]}
```'''
    qs = intake.parse_questions(text)
    assert len(qs) == 1
    assert qs[0].checklist_item == "metric"
    assert qs[0].text.startswith("What is")


def test_parse_questions_empty_array_ok():
    text = '```json\n{"questions": []}\n```'
    assert intake.parse_questions(text) == []


def test_parse_questions_caps_at_six():
    items = ",".join(
        f'{{"id":"q{i}","checklist_item":"problem","text":"q{i}?"}}' for i in range(20)
    )
    text = f'```json\n{{"questions": [{items}]}}\n```'
    assert len(intake.parse_questions(text)) == 6


def test_parse_questions_malformed_raises():
    with pytest.raises(intake.IntakeParseError):
        intake.parse_questions("no json here at all")
