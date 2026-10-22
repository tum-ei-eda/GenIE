import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('legacy_setup', Path(__file__).parents[2] / 'scripts/prepare_legacy_tools.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def test_legacy_setup_keeps_inputs_unchanged_and_emits_overrides(tmp_path):
    seal5 = tmp_path / 'original-seal5'
    logistro = tmp_path / 'original-logistro'
    (seal5 / 'seal5/tools').mkdir(parents=True)
    logistro.mkdir()
    tag_call = 'repo.create_tag(f"seal5-{label}-base", "-f")'
    (seal5 / 'seal5/tools/llvm.py').write_text(tag_call)
    (logistro / '_args.py').write_text('parser = argparse.ArgumentParser(add_help=False)')
    result = legacy.prepare(seal5, logistro, tmp_path / 'prepared')
    assert (seal5 / 'seal5/tools/llvm.py').read_text() == tag_call
    assert 'force=True' in (Path(result['paths']['seal5.src_dir']) / 'seal5/tools/llvm.py').read_text()
    assert 'allow_abbrev=False' in (Path(result['environment']['PYTHONPATH']) / 'logistro/_args.py').read_text()
    with pytest.raises(FileExistsError):
        legacy.prepare(seal5, logistro, tmp_path / 'prepared')


def test_legacy_setup_rejects_unknown_source_before_copying(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'module.py').write_text('unexpected')
    destination = tmp_path / 'destination'
    with pytest.raises(ValueError, match='Unsupported dependency'):
        legacy.patched_copy(source, destination, 'module.py', 'old', 'new')
    assert not destination.exists()
