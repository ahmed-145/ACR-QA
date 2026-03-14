"""Tests for scripts/user_study.py — survey generation and comparison report."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.user_study import (
    SURVEY_QUESTIONS,
    generate_survey_form,
)


class TestSurveyQuestions:
    """Test the survey questionnaire configuration."""

    def test_survey_has_questions(self):
        assert len(SURVEY_QUESTIONS) > 0

    def test_all_questions_have_ids(self):
        for q in SURVEY_QUESTIONS:
            assert "id" in q, f"Question missing ID: {q}"
            assert q["id"].startswith("Q"), f"Bad ID format: {q['id']}"

    def test_all_questions_have_sections(self):
        for q in SURVEY_QUESTIONS:
            assert "section" in q
            assert len(q["section"]) > 0

    def test_all_questions_have_type(self):
        valid_types = {"likert", "text", "choice"}
        for q in SURVEY_QUESTIONS:
            assert "type" in q
            assert q["type"] in valid_types, f"Invalid type: {q['type']}"

    def test_likert_questions_have_scale(self):
        for q in SURVEY_QUESTIONS:
            if q["type"] == "likert":
                assert "scale" in q, f"{q['id']} missing scale"

    def test_choice_questions_have_options(self):
        for q in SURVEY_QUESTIONS:
            if q["type"] == "choice":
                assert "options" in q, f"{q['id']} missing options"
                assert len(q["options"]) > 0

    def test_question_ids_are_unique(self):
        ids = [q["id"] for q in SURVEY_QUESTIONS]
        assert len(ids) == len(set(ids)), "Duplicate question IDs"

    def test_question_ids_are_sequential(self):
        for i, q in enumerate(SURVEY_QUESTIONS, 1):
            assert q["id"] == f"Q{i}", f"Expected Q{i}, got {q['id']}"

    def test_all_questions_have_text(self):
        for q in SURVEY_QUESTIONS:
            assert "question" in q
            assert len(q["question"]) > 10


class TestSurveyFormGeneration:
    """Test generating survey form outputs."""

    def test_generate_survey_form_creates_md(self, tmp_path):
        md_file, csv_file = generate_survey_form(str(tmp_path))
        assert md_file.exists()
        assert md_file.suffix == ".md"

    def test_generate_survey_form_creates_csv(self, tmp_path):
        md_file, csv_file = generate_survey_form(str(tmp_path))
        assert csv_file.exists()
        assert csv_file.suffix == ".csv"

    def test_md_contains_all_questions(self, tmp_path):
        md_file, _ = generate_survey_form(str(tmp_path))
        content = md_file.read_text()
        for q in SURVEY_QUESTIONS:
            assert q["question"] in content, f"Missing question: {q['id']}"

    def test_md_contains_sections(self, tmp_path):
        md_file, _ = generate_survey_form(str(tmp_path))
        content = md_file.read_text()
        sections = set(q["section"] for q in SURVEY_QUESTIONS)
        for section in sections:
            assert section in content, f"Missing section: {section}"

    def test_csv_has_header_row(self, tmp_path):
        _, csv_file = generate_survey_form(str(tmp_path))
        with open(csv_file) as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "participant_id" in header
        assert "timestamp" in header
        assert "Q1" in header

    def test_csv_has_example_row(self, tmp_path):
        _, csv_file = generate_survey_form(str(tmp_path))
        with open(csv_file) as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            example = next(reader)
        assert example[0] == "P001"

    def test_md_contains_likert_scale(self, tmp_path):
        md_file, _ = generate_survey_form(str(tmp_path))
        content = md_file.read_text()
        # Likert questions should have checkboxes
        assert "☐" in content

    def test_md_contains_choice_options(self, tmp_path):
        md_file, _ = generate_survey_form(str(tmp_path))
        content = md_file.read_text()
        # Choice questions should have their options
        choice_qs = [q for q in SURVEY_QUESTIONS if q["type"] == "choice"]
        for q in choice_qs:
            for opt in q["options"]:
                assert opt in content, f"Missing option: {opt}"

    def test_output_dir_created_if_missing(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        generate_survey_form(str(nested))
        assert nested.exists()
