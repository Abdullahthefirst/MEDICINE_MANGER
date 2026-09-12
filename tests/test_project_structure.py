from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_project_files_exist():
    required = [
        "app.py", "requirements.txt", "README.md", "BUILD_STEPS.md",
        ".streamlit/secrets.example.toml", "supabase/full_schema.sql",
        "supabase/app_setup.sql",
    ]
    assert all((ROOT / path).is_file() for path in required)


def test_schema_preserves_supplied_catalogue_numbers_and_nullable_unknowns():
    schema = (ROOT / "supabase/full_schema.sql").read_text(encoding="utf-8")
    for number in ("12759", "15115", "14225", "12144", "1785", "11665", "2132"):
        assert f"'{number}'" in schema
    assert "('CMP-MANNOSE','Mannose','kit_component','unit',null" in schema
    assert "('CMP-WFI','Water for Injection (WFI)','kit_component','ml',null" in schema


def test_no_real_secret_file_is_packaged():
    assert not (ROOT / ".streamlit/secrets.toml").exists()
