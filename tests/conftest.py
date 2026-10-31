import pytest

from structura_ai.config import settings


@pytest.fixture(autouse=True, scope="session")
def _isolated_upload_dirs(tmp_path_factory):
    """Redireciona uploads/artefatos gerados pelos testes para um diretório temporário."""
    base = tmp_path_factory.mktemp("uploads")
    generated = base / "generated"
    generated.mkdir()
    original = (settings.UPLOAD_DIR, settings.GENERATED_DIR)
    settings.UPLOAD_DIR = str(base)
    settings.GENERATED_DIR = str(generated)
    yield
    settings.UPLOAD_DIR, settings.GENERATED_DIR = original
