"""Tests for cleanup_page prompt output parsing."""

from __future__ import annotations

import pytest
from pydantic import BaseModel


class CleanedPage(BaseModel):
    """Expected output schema from cleanup_page prompt."""

    page_num: int
    paragraphs: list[dict]  # [{text, starts_mid_sentence, ends_mid_sentence}]
    corrections: list[dict]  # [{original, corrected, type}]
    is_chapter_start: bool
    chapter_title: str | None


class TestCleanupPageSchema:
    """Tests for the cleanup page output schema."""

    def test_valid_output_parses(self) -> None:
        """Valid LLM output parses correctly."""
        data = {
            "page_num": 9,
            "paragraphs": [
                {
                    "text": "Saapasparit riippuivat varaston orrella.",
                    "starts_mid_sentence": False,
                    "ends_mid_sentence": False,
                },
            ],
            "corrections": [
                {"original": "..   .", "corrected": "...", "type": "ellipsis"},
            ],
            "is_chapter_start": False,
            "chapter_title": None,
        }
        result = CleanedPage(**data)
        assert result.page_num == 9
        assert len(result.paragraphs) == 1

    def test_chapter_start_detected(self) -> None:
        """Chapter start with title."""
        data = {
            "page_num": 5,
            "paragraphs": [
                {
                    "text": "Ensimmäinen luku.",
                    "starts_mid_sentence": False,
                    "ends_mid_sentence": False,
                },
            ],
            "corrections": [],
            "is_chapter_start": True,
            "chapter_title": "I LUKU",
        }
        result = CleanedPage(**data)
        assert result.is_chapter_start is True
        assert result.chapter_title == "I LUKU"

    def test_mid_sentence_markers(self) -> None:
        """Paragraph spanning pages has markers."""
        data = {
            "page_num": 10,
            "paragraphs": [
                {
                    "text": "jatkuu edelliseltä sivulta ja päättyy tähän.",
                    "starts_mid_sentence": True,
                    "ends_mid_sentence": False,
                },
                {
                    "text": "Uusi kappale joka jatkuu seuraavalle",
                    "starts_mid_sentence": False,
                    "ends_mid_sentence": True,
                },
            ],
            "corrections": [],
            "is_chapter_start": False,
            "chapter_title": None,
        }
        result = CleanedPage(**data)
        assert result.paragraphs[0]["starts_mid_sentence"] is True
        assert result.paragraphs[1]["ends_mid_sentence"] is True

    def test_multiple_corrections(self) -> None:
        """Multiple correction types tracked."""
        data = {
            "page_num": 12,
            "paragraphs": [
                {
                    "text": "Korjattu teksti.",
                    "starts_mid_sentence": False,
                    "ends_mid_sentence": False,
                }
            ],
            "corrections": [
                {"original": "ni", "corrected": "m", "type": "ocr_char"},
                {
                    "original": "hau-\nkotus",
                    "corrected": "haukotus",
                    "type": "hyphenation",
                },
                {"original": "■", "corrected": "", "type": "artifact"},
            ],
            "is_chapter_start": False,
            "chapter_title": None,
        }
        result = CleanedPage(**data)
        assert len(result.corrections) == 3
        assert result.corrections[0]["type"] == "ocr_char"


class TestCleanupPagePromptIntegration:
    """Integration test with actual LLM call."""

    @pytest.fixture
    def sample_raw_text(self) -> str:
        """Sample OCR text from page 9."""
        return """    Saapasparit riippuivat varaston orrella omassa
hiljaiselossaan. Ne olivat uusia saappaita, ja elämä
 ja seikkailu odottivat niitä, odottivat soturien ur-
hoolliset ja nöyrät jalat. Niiden musta muhkeus
näytti välähtelevän halveksivasti toisien orsien
käytetyille saapaspareille, joissa oli kuhmuja ja
naarmuja ja muodottomuutta. Jalat ja elämä oli-
vat pidelleet niitä sangen pahoin. Kukapa tiesi
tahi tuli ajatelleeksi, että noilla surkeilla saap-
pailla oli kerran ollut oma nuoruutensa, että
upseeri oli seisonut niissä kukkulalla ja johtanut
taistelun menoa, että sotamies oli niissä hyökän-
nyt ilkeässä kuulasateessa, hyökännyt, kunnes koi-
vet oikenivat ja saappaat kiskottiin jäykistyneistä
 jaloista toisia jalankampuroita verhoamaan .    ..




Ehkäpä on nahkasaappaillekin onneksi, että tule-
vaisuus on kätkettynä ja vieläpä menneisyyskin
pimeyden peitossa ..   .

"""

    @pytest.mark.skipif(
        True,  # Skip by default - enable manually for LLM testing
        reason="Requires LLM API key and costs money",
    )
    def test_cleanup_with_real_llm(self, sample_raw_text: str) -> None:
        """Test cleanup prompt with real LLM."""
        from yamlgraph.executor import execute_prompt

        result = execute_prompt(
            "examples/ocr_cleanup/prompts/cleanup_page",
            variables={
                "page_num": 9,
                "raw_text": sample_raw_text,
                "prev_page_last_line": "",
            },
        )

        # Validate structure
        assert "paragraphs" in result
        assert "corrections" in result
        assert len(result["paragraphs"]) >= 1

        # Should have cleaned up ellipsis
        corrections = result.get("corrections", [])
        ellipsis_corrections = [c for c in corrections if c["type"] == "ellipsis"]
        assert len(ellipsis_corrections) >= 1
