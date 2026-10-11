import json
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from chatgh.cli import main
from chatgh.github import api, commands, transport


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, check=True).stdout


def repo(tmp_path, name='repo'):
    path = tmp_path / name
    git(tmp_path, 'init', '-q', str(path))
    git(path, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    git(path, 'remote', 'add', 'origin', f'https://github.com/example/{name}.git')
    return path


def key(name='repo'):
    return f'http.https://github.com/example/{name}.git.extraHeader'


def test_set_and_unset_select_the_same_origin_not_upstream(tmp_path, monkeypatch):
    path = repo(tmp_path)
    git(path, 'remote', 'add', 'upstream', 'https://github.com/other/project.git')
    git(path, 'config', 'branch.main.remote', 'upstream')
    git(path, 'config', 'branch.main.merge', 'refs/heads/main')
    git(path, 'config', 'http.https://github.com/other/project.git.extraHeader', 'keep-upstream')
    monkeypatch.chdir(path)
    commands.set_token('dummy-current', False)
    result = transport.unset_token(cwd=str(path))
    assert result['repo'] == 'example/repo'
    assert result['removed_count'] == 1
    assert subprocess.run(['git', '-C', str(path), 'config', '--local', '--get', key()], capture_output=True).returncode == 1
    assert git(path, 'config', '--get', 'http.https://github.com/other/project.git.extraHeader').strip() == 'keep-upstream'


def test_unset_clears_exact_set_field_without_token_content_detection(tmp_path, monkeypatch):
    path = repo(tmp_path)
    git(path, 'config', key(), 'expired-or-corrupt-value')
    git(path, 'config', 'review.other', 'keep')
    monkeypatch.setattr(transport, 'resolve_token_with_source', lambda *a, **kw: pytest.fail('unset must not resolve token'))
    result = transport.unset_token(cwd=str(path))
    assert result['removed_count'] == 1
    assert result['removed_keys'] == [key()]
    assert git(path, 'config', '--get', 'review.other').strip() == 'keep'
    assert transport.unset_token(cwd=str(path))['removed_count'] == 0


def test_from_config_overwrites_old_repository_value(tmp_path, monkeypatch):
    path = repo(tmp_path)
    git(path, 'config', key(), api.github_auth_extraheader('dummy-old'))
    monkeypatch.chdir(path)
    monkeypatch.setattr(api, 'get_github_config_token', lambda: 'dummy-new')
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--json-output'])
    assert result.exit_code == 0, result.output
    assert api.read_github_token_from_git(api.credential_path_from_repo('example/repo')) == 'dummy-new'
    assert 'dummy-new' not in result.output


@pytest.mark.parametrize('suffix', ['json', 'yaml'])
def test_batch_file_updates_all_targets_without_persisting_secret_in_file(tmp_path, monkeypatch, suffix):
    first, second = repo(tmp_path, 'first'), repo(tmp_path, 'second')
    data = {'version': 1, 'repositories': [{'path': 'first', 'repo': 'example/first'}, {'path': 'second', 'repo': 'example/second'}]}
    manifest = tmp_path / ('repos.' + suffix)
    manifest.write_text(json.dumps(data) if suffix == 'json' else yaml.safe_dump(data))
    before = manifest.read_bytes()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, 'get_github_config_token', lambda: 'dummy-batch')
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--file', str(manifest), '--json-output'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['total'] == 2 and payload['configured'] == 2 and payload['failed'] == 0
    for path in [first, second]:
        assert git(path, 'config', '--get', key(path.name)).strip() == api.github_auth_extraheader('dummy-batch')
    assert manifest.read_bytes() == before and 'dummy-batch' not in result.output


def test_batch_preflights_every_target_before_secret_resolution_or_writes(tmp_path, monkeypatch):
    first = repo(tmp_path, 'first')
    before = (first / '.git/config').read_bytes()
    manifest = tmp_path / 'repos.json'
    manifest.write_text(json.dumps({'repositories': [str(first), str(tmp_path / 'missing')]}))
    monkeypatch.setattr(api, 'get_github_config_token', lambda: pytest.fail('secret read before preflight'))
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--file', str(manifest)])
    assert result.exit_code != 0
    assert 'repository' in result.output.lower() and 'No such option' not in result.output
    assert (first / '.git/config').read_bytes() == before


def test_from_config_and_explicit_token_are_mutually_exclusive():
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--token', 'dummy'])
    assert result.exit_code != 0
    assert 'cannot combine' in result.output.lower()


def test_unset_has_no_broad_all_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(repo(tmp_path))
    result = CliRunner().invoke(main, ['unset-token', '--all'])
    assert result.exit_code == 2 and 'No such option' in result.output


def test_batch_dry_run_and_duplicate_paths_do_not_write(tmp_path, monkeypatch):
    first = repo(tmp_path, 'first')
    before = (first / '.git/config').read_bytes()
    manifest = tmp_path / 'repos.json'
    manifest.write_text(json.dumps({'repositories': [str(first), str(first)]}))
    monkeypatch.setattr(api, 'get_github_config_token', lambda: 'dummy-plan')
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--file', str(manifest), '--dry-run', '--json-output'])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload['requested'] == 2 and payload['total'] == 1 and payload['duplicates_skipped'] == 1
    assert payload['configured'] == 0 and payload['failed'] == 0
    assert (first / '.git/config').read_bytes() == before


def test_batch_reports_partial_failure_and_preserves_foreign_lock(tmp_path, monkeypatch):
    first, second = repo(tmp_path, 'first'), repo(tmp_path, 'second')
    foreign = second / '.git/config.lock'
    foreign.write_text('owned by another writer\n')
    manifest = tmp_path / 'repos.json'
    manifest.write_text(json.dumps({'repositories': [str(first), str(second)]}))
    monkeypatch.setattr(api, 'get_github_config_token', lambda: 'dummy-current')
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--file', str(manifest), '--json-output'])
    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload['total'] == 2 and payload['configured'] == 1 and payload['failed'] == 1
    assert foreign.read_text() == 'owned by another writer\n'
    assert 'dummy-current' not in result.output


@pytest.mark.parametrize('data', [
    {'repositories': [], 'token': 'never-write-this'},
    {'version': True, 'repositories': []},
    {'repositories': [{'path': 'missing', 'token': 'never-write-this'}]},
])
def test_manifest_rejects_secret_fields_and_invalid_schema(tmp_path, monkeypatch, data):
    manifest = tmp_path / 'bad.json'
    manifest.write_text(json.dumps(data))
    monkeypatch.setattr(api, 'get_github_config_token', lambda: pytest.fail('schema must precede token read'))
    result = CliRunner().invoke(main, ['set-token', '--from-config', '--file', str(manifest)])
    assert result.exit_code != 0
    assert 'never-write-this' not in result.output
