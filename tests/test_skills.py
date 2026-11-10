"""Offline behavior checks; all filesystem and Git mutations use temporary paths."""
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/reverse-engineering-cherry-picking/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM='1', PYTHONDONTWRITEBYTECODE='1')
        for key in list(self.env):
            if key.startswith(('GIT_AUTHOR_', 'GIT_COMMITTER_')):
                del self.env[key]

    def run_command(self, args, cwd=None, check=True):
        result = subprocess.run([str(a) for a in args], cwd=cwd or self.work,
                                env=self.env, capture_output=True, text=True, timeout=30)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def git(self, repo, *args):
        return self.run_command(['git', '-C', repo, *args]).stdout.strip()

    def init_repo(self, name):
        repo = self.work / name
        self.run_command(['git', 'init', '-q', repo])
        self.git(repo, 'config', 'user.name', 'Fixture Engineer')
        self.git(repo, 'config', 'user.email', 'fixture@example.invalid')
        return repo

    def commit(self, repo, name, content, subject):
        (repo / name).write_text(content)
        self.git(repo, 'add', name)
        self.git(repo, 'commit', '-qm', subject)
        return self.git(repo, 'rev-parse', 'HEAD')

    def test_help_without_identity_or_network(self):
        scripts = sorted(SCRIPTS.glob('*.py')) + sorted(SCRIPTS.glob('*.sh'))
        scripts += [ROOT / 'install.sh', ROOT / 'bundle.sh']
        for script in scripts:
            with self.subTest(script=script.name):
                runtime = sys.executable if script.suffix == '.py' else 'bash'
                result = self.run_command([runtime, script, '-h'])
                self.assertTrue(result.stdout.strip())

    def test_preflight_rejects_missing_and_empty_inputs(self):
        for directory in [self.work / 'missing', self.work]:
            result = self.run_command([sys.executable, SCRIPTS / 'preflight.py',
                                       '--dt', directory], check=False)
            self.assertNotEqual(result.returncode, 0)
        (self.work / 'device.mk').write_text('PRODUCT_DEVICE := fixture\n')
        self.run_command([sys.executable, SCRIPTS / 'preflight.py', '--dt', self.work])
        result = self.run_command([sys.executable, SCRIPTS / 'preflight.py', '--dt',
                                   self.work, '--hw', self.work / 'missing'], check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_preflight_detects_typed_property_conflicts(self):
        module = load('preflight')
        (self.work / 'property_contexts').write_text(
            'vendor.fixture u:object_r:first_prop:s0 exact string\n'
            'vendor.fixture u:object_r:second_prop:s0 exact string\n')
        module.check_sepolicy([str(self.work)])
        self.assertEqual(len(module.ERRORS), 1)
        self.assertIn('first_prop', module.ERRORS[0][1])
        self.assertIn('second_prop', module.ERRORS[0][1])

    def test_preflight_counts_same_file_declarations_once_per_scan(self):
        module = load('preflight')
        (self.work / 'types.te').write_text('type fixture, domain;\ntype fixture, domain;\n')
        module.check_sepolicy([str(self.work), str(self.work)])
        self.assertEqual(len(module.ERRORS), 1)
        (self.work / 'types.te').write_text('type fixture, domain;\n')
        module.ERRORS.clear()
        module.check_sepolicy([str(self.work), str(self.work)])
        self.assertEqual(module.ERRORS, [])

    def test_preflight_rejects_malformed_and_duplicate_vintf(self):
        module = load('preflight')
        module.check_vintf([('broken.xml', '<manifest>')])
        self.assertEqual(len(module.ERRORS), 1)
        module.ERRORS.clear()
        hal = '<hal format="aidl"><name>vendor.fixture</name><fqname>IFoo/default</fqname></hal>'
        module.check_vintf([('duplicate.xml', '<manifest>' + hal * 2 + '</manifest>')])
        self.assertEqual(len(module.ERRORS), 1)

    def test_mapping_does_not_rewrite_hunk_payload(self):
        module = load('fetch-patch')
        header = ('diff --git a/old/file b/old/file\n'
                  '--- a/old/file\n+++ b/old/file\n')
        payload = '@@ -1 +1 @@\n--- a/old/payload\n+++ b/old/payload\n'
        result, _, _ = module.rewrite(header + payload, [('old/', 'new/')], [], [])
        self.assertIn('--- a/new/file\n+++ b/new/file', result)
        self.assertTrue(result.endswith(payload))
        quoted = 'diff --git "a/a b" "b/a b"\n'
        self.assertEqual(module.rewrite(quoted, [], [], [])[0], quoted)

    def test_patch_trial_uses_target_identity_and_relative_mbox(self):
        source = self.init_repo('source')
        self.commit(source, 'file', 'before\n', 'Initial')
        target = self.work / 'target'
        self.run_command(['git', 'clone', '-q', source, target])
        self.git(target, 'config', 'user.name', 'Target Engineer')
        self.git(target, 'config', 'user.email', 'target@example.invalid')
        before = self.git(target, 'rev-parse', 'HEAD')
        self.commit(source, 'file', 'after\n', 'Fix fixture')
        patch_text = self.run_command(['git', '-C', source, 'format-patch', '-1', '--stdout']).stdout
        (self.work / 'input.mbox').write_text(patch_text)
        self.run_command([sys.executable, SCRIPTS / 'fetch-patch.py', 'input.mbox',
                          '-o', 'output.mbox', '-C', target, '--check'])
        self.assertEqual(self.git(target, 'rev-parse', 'HEAD'), before)
        self.assertEqual((target / 'file').read_text(), 'before\n')
        self.assertEqual(self.git(target, 'status', '--porcelain'), '')
        self.assertEqual(len(self.git(target, 'worktree', 'list').splitlines()), 1)

    def test_upstream_same_subject_is_not_have(self):
        source = self.init_repo('source')
        self.commit(source, 'first', 'base\n', 'Initial')
        base = self.git(source, 'rev-parse', 'HEAD')
        self.git(source, 'checkout', '-qb', 'upstream')
        change = self.commit(source, 'first', 'changed\n', 'Device: Fix')
        self.git(source, 'checkout', '-qb', 'fork', base)
        self.commit(source, 'second', 'different change\n', 'Device: Fix')
        target = self.work / 'target'
        self.run_command(['git', 'clone', '-q', '--branch', 'fork', source, target])
        self.git(target, 'config', 'user.name', 'Target Engineer')
        self.git(target, 'config', 'user.email', 'target@example.invalid')
        before = self.git(target, 'rev-parse', 'HEAD')
        result = self.run_command(['bash', SCRIPTS / 'upstream-diff.sh', '-C', target,
                                   '-u', source, '-b', 'upstream', '-f', 'HEAD'])
        self.assertRegex(result.stdout, r'CLEAN\s+' + change[:8])
        self.assertEqual(self.git(target, 'rev-parse', 'HEAD'), before)
        self.assertEqual(self.git(target, 'status', '--porcelain'), '')

    def test_upstream_reverted_patch_is_not_have(self):
        repo = self.init_repo('source')
        base = self.commit(repo, 'file', 'before\n', 'Initial')
        self.git(repo, 'checkout', '-qb', 'upstream')
        change = self.commit(repo, 'file', 'after\n', 'Fix fixture')
        self.git(repo, 'checkout', '-qb', 'fork')
        self.git(repo, 'revert', '--no-edit', change)
        result = self.run_command(['bash', SCRIPTS / 'upstream-diff.sh', '-C', repo,
                                   '-u', repo, '-b', 'upstream', '-f', 'fork', '-s', base])
        self.assertRegex(result.stdout, r'CLEAN\s+' + change[:8])
        self.assertEqual((repo / 'file').read_text(), 'before\n')

    def test_empty_blob_list_is_valid(self):
        repo = self.init_repo('source')
        old = self.commit(repo, 'proprietary-files.txt', '# empty\n', 'Initial')
        new = self.commit(repo, 'proprietary-files.txt', 'vendor/lib64/libfixture.so\n', 'Add blob')
        result = self.run_command(['bash', SCRIPTS / 'blob-drops.sh', '-C', repo, old, new])
        self.assertIn('added 1', result.stdout)

    def test_followup_search_paginates(self):
        module = load('followups')
        calls = []
        def fake(path):
            calls.append(path)
            return [{'sha': str(i)} for i in range(100)] if path.endswith('&page=1') else [{'sha': 'last'}]
        with patch.object(module, 'gh', side_effect=fake):
            self.assertEqual(len(list(module.pages('endpoint?sha=pinned'))), 101)
        self.assertEqual(len(calls), 2)

    def test_credit_for_users_own_upstream_commit(self):
        module = load('credit')
        response = {'commit': {'author': {'name': 'Engineer', 'email': 'a@example.invalid'},
                               'message': 'Own original change'}, 'html_url': 'https://example.invalid/commit/1'}
        output = io.StringIO()
        with patch.object(sys, 'argv', ['credit.py', 'O/R', 'SHA', '--me', 'Engineer <a@example.invalid>']), \
             patch.object(module, 'gh', return_value=response), contextlib.redirect_stdout(output):
            module.main()
        self.assertIn('author: Engineer <a@example.invalid>', output.getvalue())
        self.assertNotIn('Co-authored-by:', output.getvalue())

    def test_live_avc_read_failure_is_not_success(self):
        module = load('avc2rules')
        failure = subprocess.CompletedProcess([], 1, '', 'permission denied')
        with patch.object(sys, 'argv', ['avc2rules.py', '--live']), \
             patch.object(module.subprocess, 'run', return_value=failure), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(module.main(), 1)

    def vendor_fixture(self, args, moved=False):
        module = load('vendor-api-commit')
        bp = 'cc_prebuilt_library_shared {\n    name: "libfixture",\n    srcs: ["proprietary/libfixture.so"],\n}\n'
        files = {'Android.bp': bp.encode(), 'fixture-vendor.mk': b'PRODUCT_PACKAGES += libfixture\n',
                 'proprietary/libfixture.so': b'fixture', 'proprietary/bin/helper': b'original'}
        entries = [{'path': p, 'type': 'blob', 'mode': '100755' if p.endswith('/helper') else '100644',
                    'sha': hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()}
                   for p, data in files.items()]
        writes = []
        reads = 0

        def api(path, method='GET', body=None, raw=False):
            nonlocal reads
            if method != 'GET':
                writes.append((path, method, body))
                return {'sha': 'new-commit' if path.endswith('/git/commits') else 'new-object'}
            if path.endswith('/git/ref/heads/main'):
                reads += 1
                return {'object': {'sha': 'moved' if moved and reads > 1 else 'base'}}
            if path.endswith('/git/commits/base'):
                return {'tree': {'sha': 'base-tree'}}
            if '/git/trees/' in path:
                return {'tree': entries, 'truncated': False}
            if '/contents/' in path:
                return files[path.split('/contents/', 1)[1].split('?', 1)[0]]
            if '/compare/' in path:
                return {'files': [{'filename': 'proprietary/bin/helper', 'status': 'modified'}]}
            raise AssertionError(path)

        failure = None
        with patch.object(sys, 'argv', ['vendor-api-commit.py', '--repo', 'O/R', '--branch', 'main', *args]), \
             patch.object(module, 'gh', side_effect=api), \
             patch.object(module, 'me', return_value='Engineer <engineer@example.invalid>') as identity, \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                module.main()
            except SystemExit as exc:
                failure = exc.code
            if '--apply' not in args:
                identity.assert_not_called()
        return writes, failure

    def test_vendor_dry_run_and_identical_put_do_not_write(self):
        replacement = self.work / 'helper'
        replacement.write_bytes(b'changed')
        args = ['--put', f'{replacement}=proprietary/bin/helper']
        writes, failure = self.vendor_fixture(args)
        self.assertIsNone(failure)
        self.assertEqual(writes, [])
        replacement.write_bytes(b'original')
        writes, failure = self.vendor_fixture(args + ['--apply', '-m', 'No change'])
        self.assertIsNone(failure)
        self.assertEqual(writes, [])

    def test_vendor_apply_preserves_executable_mode(self):
        replacement = self.work / 'helper'
        replacement.write_bytes(b'changed')
        writes, failure = self.vendor_fixture(['--put', f'{replacement}=proprietary/bin/helper',
                                               '--apply', '-m', 'Update helper'])
        self.assertIsNone(failure)
        tree = next(body for path, method, body in writes if path.endswith('/git/trees'))
        self.assertEqual(tree['tree'][0]['mode'], '100755')
        self.assertEqual(writes[-1][1], 'PATCH')
        self.assertFalse(writes[-1][2]['force'])

    def test_vendor_rejects_stale_branch_and_build_file_bypass(self):
        replacement = self.work / 'helper'
        replacement.write_bytes(b'changed')
        writes, failure = self.vendor_fixture(['--put', f'{replacement}=proprietary/bin/helper',
                                               '--apply', '-m', 'Update helper'], moved=True)
        self.assertIsNotNone(failure)
        self.assertEqual(writes, [])
        writes, failure = self.vendor_fixture(['--put', f'{replacement}=Android.bp'])
        self.assertIsNotNone(failure)
        self.assertEqual(writes, [])
        writes, failure = self.vendor_fixture(['--drop-file', 'Android.bp'])
        self.assertIsNotNone(failure)
        self.assertEqual(writes, [])

    def test_installer_scopes_destinations_and_preserves_foreign_links(self):
        target = self.work / 'agent skills'
        target.mkdir()
        foreign = self.work / 'foreign'
        foreign.mkdir()
        link = target / 'rom-device-dev'
        link.symlink_to(foreign, target_is_directory=True)
        self.run_command(['bash', ROOT / 'install.sh', '--to', target])
        self.assertEqual(link.resolve(), foreign)
        self.run_command(['bash', ROOT / 'install.sh', '--to', target, '--force'])
        self.assertEqual(link.resolve(), ROOT / 'skills/rom-device-dev')
        backups = list(target.glob('rom-device-dev.bak.*/rom-device-dev'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].resolve(), foreign)
        self.run_command(['bash', ROOT / 'install.sh', '--to', target, '--remove'])
        self.assertFalse(link.is_symlink())
        self.assertEqual(backups[0].resolve(), foreign)
        self.assertNotEqual(self.run_command(['bash', ROOT / 'install.sh', '--to'], check=False).returncode, 0)

    def test_bundle_contains_source_and_upstream_notices(self):
        copy = self.work / 'repo'
        shutil.copytree(ROOT / 'skills', copy / 'skills', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy2(ROOT / 'bundle.sh', copy / 'bundle.sh')
        self.run_command(['bash', copy / 'bundle.sh'])
        for skill in (copy / 'skills').iterdir():
            bundle = (copy / 'dist' / (skill.name + '.md')).read_text()
            for path in [skill / 'SKILL.md', skill / 'CREDITS.md', skill / 'LICENSE', *skill.glob('references/*.md')]:
                if path.is_file():
                    self.assertIn(path.read_text(), bundle)

    def test_local_markdown_links_resolve(self):
        for path in [ROOT / 'README.md', ROOT / 'AGENTS.md', *ROOT.glob('skills/**/*.md')]:
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                destination = target.split('#', 1)[0]
                self.assertTrue((path.parent / destination).exists(), f'{path}: {target}')


if __name__ == '__main__':
    unittest.main()
