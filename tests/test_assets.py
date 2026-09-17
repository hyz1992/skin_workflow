"""Independent byte/geometry fixtures; no original-project assets or services."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.agents/skills/ui-skin-assets/scripts/assets.py'
SPEC = importlib.util.spec_from_file_location('ui_skin_assets', SCRIPT)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        image = Image.new('RGBA', (40, 20))
        # Includes holes, partial alpha and nonzero RGB under fully transparent pixels.
        for y in range(3, 17):
            for x in range(3, 37):
                image.putpixel((x, y), (x * 5, y * 9, 80, 128 if x == 3 else 255))
        image.putpixel((10, 10), (20, 30, 40, 0))
        image.save(self.root / 'button.png')
        self.manifest = tool.example()
        asset = self.manifest['assets'][0]
        asset.update(sha256=tool.inspect(self.root / 'button.png')['sha256'], pixelSize=[40, 20], displaySize=[80, 40])
        self.path = self.root / 'assets.json'
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding='utf-8')

    def test_real_decode_and_check(self):
        _, report = tool.check(self.path)
        self.assertEqual(report['technicalStatus'], 'passed')
        self.assertEqual(report['visualApproval'], 'not-assessed')
        info = report['assets'][0]
        self.assertEqual(info['visibleBounds'], [3, 3, 37, 17])
        self.assertGreater(info['alpha']['semitransparent'], 0)

    def test_truncated_png_is_not_a_valid_header_only_image(self):
        (self.root / 'bad.png').write_bytes((self.root / 'button.png').read_bytes()[:24])
        with self.assertRaises(tool.Invalid):
            tool.inspect(self.root / 'bad.png')

    def test_hash_and_pixel_identity(self):
        for field, value in [('sha256', 'a' * 64), ('pixelSize', [20, 10])]:
            with self.subTest(field=field):
                old = self.manifest['assets'][0][field]
                self.manifest['assets'][0][field] = value; self.save()
                with self.assertRaises(tool.Invalid): tool.check(self.path)
                self.manifest['assets'][0][field] = old

    def test_opaque_invisible_and_false_background_declarations(self):
        for alpha, policy in [(255, 'required'), (0, 'required'), (0, 'any'), (128, 'opaque')]:
            with self.subTest(alpha=alpha, policy=policy):
                Image.new('RGBA', (40, 20), (100, 80, 60, alpha)).save(self.root / 'button.png')
                self.manifest['assets'][0].update(sha256=tool.inspect(self.root / 'button.png')['sha256'], transparency=policy)
                self.save()
                with self.assertRaises(tool.Invalid): tool.check(self.path)

    def test_declared_opaque_background_is_supported(self):
        Image.new('RGB', (40, 20), '#234567').save(self.root / 'button.png')
        self.manifest['assets'][0].update(sha256=tool.inspect(self.root / 'button.png')['sha256'], transparency='opaque')
        self.save(); tool.check(self.path)

    def test_path_traversal_and_symlinks(self):
        (self.root / 'link.png').symlink_to(self.root / 'button.png')
        for name in ['../button.png', '/button.png', 'a//b.png', 'a\\b.png', 'C:/b.png', 'link.png']:
            with self.subTest(name=name):
                self.manifest['assets'][0]['file'] = name; self.save()
                with self.assertRaises(tool.Invalid): tool.check(self.path)

    def test_duplicate_roles_and_files(self):
        self.manifest['assets'].append(copy.deepcopy(self.manifest['assets'][0]))
        self.save()
        with self.assertRaises(tool.Invalid): tool.check(self.path)
        self.manifest['assets'][1]['key'] = 'other-role'; self.save()
        with self.assertRaises(tool.Invalid): tool.check(self.path)

    def test_nonuniform_scaling_requires_explicit_explanation(self):
        asset = self.manifest['assets'][0]
        asset['displaySize'] = [90, 40]; self.save()
        with self.assertRaises(tool.Invalid): tool.check(self.path)
        asset.update(resizeMode='stretch', notes=''); self.save()
        with self.assertRaises(tool.Invalid): tool.check(self.path)
        asset['notes'] = 'Intentional geometry-only background stretch'; self.save()
        tool.check(self.path)

    def test_nonfinite_and_boolean_geometry_rejected(self):
        for value in [[float('nan'), 20], [True, 20], [0, 20]]:
            self.manifest['assets'][0]['displaySize'] = value; self.save()
            with self.assertRaises(tool.Invalid): tool.check(self.path)

    def test_duplicate_json_fields_rejected(self):
        self.path.write_text('{"format":"x","format":"ui-skin-assets-v1"}')
        with self.assertRaisesRegex(tool.Invalid, 'duplicate JSON key'): tool.check(self.path)

    def test_crop_preserves_exact_rgba_pixels(self):
        output = self.root / 'crop.png'
        result = tool.slice_png(self.root / 'button.png', [2, 2, 12, 12], output)
        with Image.open(self.root / 'button.png') as image:
            expected = image.convert('RGBA').crop((2, 2, 14, 14)).tobytes()
        with Image.open(output) as image: self.assertEqual(image.tobytes(), expected)
        self.assertTrue(result['provenance']['decodedPixelsEqual'])
        with self.assertRaises(FileExistsError): tool.slice_png(self.root / 'button.png', [2, 2, 12, 12], output)

    def test_crop_out_of_bounds_does_not_create_output(self):
        output = self.root / 'crop.png'
        with self.assertRaises(tool.Invalid): tool.slice_png(self.root / 'button.png', [39, 0, 2, 1], output)
        self.assertFalse(output.exists())

    def test_preview_embeds_original_bytes_and_escapes_labels(self):
        import base64
        self.manifest['assets'][0]['label'] = '</h2><script>alert(1)</script>'
        self.save(); output = self.root / 'review.html'
        before = (self.root / 'button.png').read_bytes()
        tool.preview(self.path, output)
        text = output.read_text()
        self.assertIn(base64.b64encode(before).decode(), text)
        self.assertNotIn('<script>alert(1)</script>', text)
        self.assertEqual((self.root / 'button.png').read_bytes(), before)
        with self.assertRaises(FileExistsError): tool.preview(self.path, output)

    def test_cli_failure_is_nonzero_without_fake_success(self):
        run = subprocess.run([sys.executable, str(SCRIPT), 'check', str(self.root / 'missing.json')], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, '')
        self.assertIn('ERROR:', run.stderr)

    def test_relocated_skill_bundle_runs_outside_project(self):
        relocated = self.root / 'different-project' / '.agents/skills'
        shutil.copytree(ROOT / '.agents/skills', relocated, ignore=shutil.ignore_patterns('__pycache__'))
        script = relocated / 'ui-skin-assets/scripts/assets.py'
        run = subprocess.run([sys.executable, '-I', str(script), 'check', str(self.path)], cwd=self.root,
                             env={k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['technicalStatus'], 'passed')


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = self.root / 'source'; self.source.mkdir()
        (self.source / 'prototype.html').write_text('<img src="images/a.png"><script src="page.js"></script>')
        (self.source / 'page.js').write_text('document.title="Demo";')
        (self.source / 'images').mkdir(); (self.source / 'images/a.png').write_bytes(b'identity fixture')
        self.output = self.root / 'frozen'

    def test_snapshot_is_relocatable_and_byte_exact(self):
        result = tool.snapshot(self.source, 'prototype.html', self.output)
        self.assertEqual(result['files'], 3)
        self.assertEqual(result['offlineExecution'], 'not-assessed')
        moved = self.root / 'elsewhere'; shutil.move(str(self.output), moved)
        shutil.rmtree(self.source)
        tool.verify_snapshot(moved)

    def test_tamper_missing_extra_and_entry_mismatch(self):
        tool.snapshot(self.source, 'prototype.html', self.output)
        for change in ['tamper', 'missing', 'extra', 'entry']:
            with self.subTest(change=change):
                target = self.root / change; shutil.copytree(self.output, target)
                if change == 'tamper': (target / 'page.js').write_text('changed')
                elif change == 'missing': (target / 'page.js').unlink()
                elif change == 'extra': (target / 'extra.txt').write_text('unexpected')
                else:
                    record = json.loads((target / 'snapshot.json').read_text()); record['entry'] = 'absent.html'
                    (target / 'snapshot.json').write_text(json.dumps(record))
                with self.assertRaises(tool.Invalid): tool.verify_snapshot(target)

    def test_refuses_nested_output_overwrite_and_symlink(self):
        with self.assertRaises(tool.Invalid): tool.snapshot(self.source, 'prototype.html', self.source / 'nested')
        tool.snapshot(self.source, 'prototype.html', self.output)
        with self.assertRaises(tool.Invalid): tool.snapshot(self.source, 'prototype.html', self.output)
        (self.source / 'link').symlink_to(self.source / 'page.js')
        with self.assertRaises(tool.Invalid): tool.snapshot(self.source, 'prototype.html', self.root / 'other')
        self.assertFalse((self.root / 'other').exists())


if __name__ == '__main__':
    unittest.main()
