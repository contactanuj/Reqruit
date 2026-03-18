"""Tests for JoiningPrepService."""

from src.services.joining_prep_service import JoiningPrepService


class TestLocaleRouting:
    def test_india_locale_returns_india_prep(self):
        service = JoiningPrepService()
        result = service.get_joining_prep("IN")
        assert len(result) > 0
        categories = [item.category for item in result]
        assert "PF Transfer" in categories

    def test_us_locale_returns_us_prep(self):
        service = JoiningPrepService()
        result = service.get_joining_prep("US")
        assert len(result) > 0
        categories = [item.category for item in result]
        assert "I-9 Verification" in categories

    def test_unsupported_locale_returns_empty(self):
        service = JoiningPrepService()
        result = service.get_joining_prep("FR")
        assert result == []

    def test_empty_locale_returns_empty(self):
        service = JoiningPrepService()
        result = service.get_joining_prep("")
        assert result == []

    def test_locale_case_insensitive(self):
        service = JoiningPrepService()
        result_lower = service.get_joining_prep("in")
        result_upper = service.get_joining_prep("IN")
        assert len(result_lower) == len(result_upper)

    def test_locale_whitespace_stripped(self):
        service = JoiningPrepService()
        result = service.get_joining_prep("  US  ")
        assert len(result) > 0


class TestIndiaPrep:
    def test_pf_transfer_section_present(self):
        service = JoiningPrepService()
        result = service.get_india_prep()
        pf = [item for item in result if item.category == "PF Transfer"]
        assert len(pf) == 1
        assert "UAN" in pf[0].checklist[0]

    def test_bgv_checklist_present(self):
        service = JoiningPrepService()
        result = service.get_india_prep()
        bgv = [item for item in result if item.category == "BGV"]
        assert len(bgv) == 1
        checklist_text = " ".join(bgv[0].checklist)
        assert "Aadhaar" in checklist_text
        assert "PAN" in checklist_text

    def test_joining_docs_present(self):
        service = JoiningPrepService()
        result = service.get_india_prep()
        docs = [item for item in result if item.category == "Joining Documentation"]
        assert len(docs) == 1
        checklist_text = " ".join(docs[0].checklist)
        assert "Relieving letter" in checklist_text
        assert "pay slips" in checklist_text

    def test_all_critical_documents_listed(self):
        service = JoiningPrepService()
        result = service.get_india_prep()
        all_checklist = " ".join(
            " ".join(item.checklist) for item in result
        )
        for doc in ["Aadhaar", "PAN", "Relieving letter", "pay slips"]:
            assert doc in all_checklist, f"Missing: {doc}"

    def test_items_are_locale_specific(self):
        service = JoiningPrepService()
        result = service.get_india_prep()
        assert all(item.locale_specific for item in result)


class TestUSPrep:
    def test_i9_section_present(self):
        service = JoiningPrepService()
        result = service.get_us_prep()
        i9 = [item for item in result if item.category == "I-9 Verification"]
        assert len(i9) == 1

    def test_i9_mentions_3_day_deadline(self):
        service = JoiningPrepService()
        result = service.get_us_prep()
        i9 = [item for item in result if item.category == "I-9 Verification"][0]
        checklist_text = " ".join(i9.checklist)
        assert "3 business days" in checklist_text

    def test_benefits_enrollment_present(self):
        service = JoiningPrepService()
        result = service.get_us_prep()
        benefits = [item for item in result if item.category == "Benefits Enrollment"]
        assert len(benefits) == 1

    def test_401k_section_present(self):
        service = JoiningPrepService()
        result = service.get_us_prep()
        k401 = [item for item in result if item.category == "401k Rollover"]
        assert len(k401) == 1

    def test_fsa_hsa_present(self):
        service = JoiningPrepService()
        result = service.get_us_prep()
        fsa = [item for item in result if item.category == "FSA/HSA Setup"]
        assert len(fsa) == 1

    def test_items_are_locale_specific(self):
        service = JoiningPrepService()
        result = service.get_us_prep()
        assert all(item.locale_specific for item in result)
