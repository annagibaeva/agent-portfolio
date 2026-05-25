import pytest
import main


def test_prd_filename_kebab_with_run_id():
    name = main.prd_filename("Dark Mode Toggle!", "run-20260522-120000-abcdef")
    assert name == "prd-dark-mode-toggle-run-20260522-120000-abcdef.md"


def test_load_answers_file_parses_qa(tmp_path):
    f = tmp_path / "ans.txt"
    f.write_text("metric: 30% adoption\npersona: IT admins\n", encoding="utf-8")
    answers = main.load_answers_file(f)
    assert answers["metric"] == "30% adoption"
    assert answers["persona"] == "IT admins"


def test_answer_for_question_uses_checklist_item():
    import intake
    q = intake.Question(id="q1", checklist_item="metric", text="metric?")
    answers = {"metric": "30% adoption"}
    assert main.answer_for(q, answers) == "30% adoption"


def test_answer_for_missing_returns_guess_sentinel():
    import intake
    q = intake.Question(id="q1", checklist_item="scope", text="scope?")
    assert main.answer_for(q, {}) == "guess"
