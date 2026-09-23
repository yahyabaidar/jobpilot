from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.mark.django_db
@patch("apps.jobs.management.commands.import_jobs.IMPORTERS")
def test_command_passes_contract_type_and_keywords_to_importer(mock_importers):
    mock_importer_instance = mock_importers.__getitem__.return_value.return_value
    mock_importer_instance.fetch.return_value = []
    mock_importers.keys.return_value = ["france_travail"]

    call_command(
        "import_jobs",
        "--source",
        "france_travail",
        "--limit",
        "5",
        "--contract-type",
        "E2,FS",
        "--keywords",
        "python,java",
        stdout=StringIO(),
    )

    mock_importer_instance.fetch.assert_called_once_with(
        limit=5, contract_type="E2,FS", keywords="python,java"
    )


@pytest.mark.django_db
@patch("apps.jobs.management.commands.import_jobs.IMPORTERS")
def test_command_defaults_contract_type_and_keywords_to_none(mock_importers):
    mock_importer_instance = mock_importers.__getitem__.return_value.return_value
    mock_importer_instance.fetch.return_value = []
    mock_importers.keys.return_value = ["france_travail"]

    call_command("import_jobs", "--source", "france_travail", stdout=StringIO())

    mock_importer_instance.fetch.assert_called_once_with(
        limit=50, contract_type=None, keywords=None
    )
