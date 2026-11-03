import ast
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from chord_detection_claim_audit import __version__, phrases
from chord_detection_claim_audit.audit import audit, claims, evidence, main, normalize

EXPECTED_CHORD = (
    'chord detection',
    'detects chords',
    'detect chords',
    'chord recognition',
    'recognizes chords',
    'recognises chords',
    'chord estimation',
    'estimates chords',
    'estimate chords',
    'chord identification',
    'identifies chords',
    'identify chords',
    'chord tracking',
    'tracks chords',
    'track chords',
    'chord analysis',
    'analyses chords',
    'analyzes chords',
    'automatic chord detection',
    'real time chord detection',
    'chord detector',
    'chord tracker',
    'chord estimator',
    'musical chord detection',
    'detects musical chords',
    'chord progression detection',
    'detects chord progressions',
    'chord progression recognition',
    'recognizes chord progressions',
    'chord classification',
    'classifies chords',
    'chord labeling',
    'labels chords',
    'chord labelling',
    'supports chord detection',
    'supports chord recognition',
    'chord detection algorithm',
    'chord recognition algorithm',
    'detects chord changes',
    'chord change detection',
    'chord progression estimation',
    'estimates chord progressions',
    'chord progression tracking',
    'tracks chord progressions',
    'chord progression analysis',
    'analyses chord progressions',
    'analyzes chord progressions',
    'detects chord progression',
    'audio chord detection',
    'audio chord recognition',
)
EXPECTED_NOCHORD = (
    'no chord detection',
    'does not detect chords',
    'without chord detection',
    'no chord recognition',
    'does not recognize chords',
    'does not recognise chords',
    'without chord recognition',
    'no chord estimation',
    'does not estimate chords',
    'without chord estimation',
    'no chord tracking',
    'does not track chords',
    'chord detection not supported',
    'does not support chord detection',
    'cannot detect chords',
    'never detects chords',
    'no chord identification',
    'does not identify chords',
    'no chord classification',
    'does not classify chords',
    'chord detection unavailable',
    'does not detect chord changes',
    'no chord detector',
    'no chord tracker',
)
GENERIC_NAMES = (
    'detect_chords',
    'estimate_chords',
    'get_chords',
    'chord_detect',
    'extract_chords',
    'recognize_chords',
    'recognise_chords',
    'chord_recognition',
    'identify_chords',
    'chord_identify',
    'chord_track',
    'track_chords',
    'detect_chord',
    'estimate_chord',
    'get_chord',
    'predict_chords',
    'chord_predict',
    'analyze_chords',
    'analyse_chords',
    'classify_chords',
    'label_chords',
    'chord_label',
    'detect_chord_progression',
    'estimate_chord_progression',
    'track_chord_progression',
)
GOOD = {
    'essentia': 'import essentia\nessentia.ChordsDetection()',
    'essentia_chain': 'import essentia\nessentia.standard.ChordsDetection()',
    'essentia_beats': 'import essentia\nessentia.ChordsDetectionBeats()',
    'essentia_alias': 'import essentia as e\ne.standard.ChordsDetectionBeats()',
    'essentia_shadow_exception': 'import essentia\ndef ChordsDetection(): pass\nessentia.ChordsDetection()',
}
BAD = {
    'bare_imports': 'import librosa, aubio, essentia',
    'load': 'import librosa\nlibrosa.load(path)',
    'soundfile': 'import soundfile\nsoundfile.read(path)',
    'wave': 'import wave\nwave.open(path).readframes(100)',
    'torchaudio': 'import torchaudio\ntorchaudio.load(path)',
    'capture': 'mic.listen(); mic.record(); sounddevice.rec(); stream.read()',
    'playback': 'audio.play(); sounddevice.play(y)',
    'speech': 'model.transcribe(y); recognizer.recognize_google(y); engine.stt(y)',
    'tts': 'engine.say(text); engine.synthesize(text)',
    'vad': 'vad.is_speech(y); model.get_speech_timestamps(y); Pipeline.from_pretrained("segmentation")',
    'keyword': 'pvporcupine.create(); Model().predict(y); engine.detect_keyword(y)',
    'verification': 'model.verify_files(a,b); encoder.embed_utterance(a); engine.verify_speaker(a,b)',
    'diarization': 'Pipeline.from_pretrained("pyannote/speaker-diarization"); engine.diarize(y)',
    'noise': 'noisereduce.reduce_noise(y); df.enhance.enhance(y); engine.suppress_noise(y); engine.remove_noise(y)',
    'fingerprinting': 'acoustid.fingerprint_file(path); Dejavu().recognize(path); engine.fingerprint_audio(y)',
    'events': 'AudioTagging().inference(y); hub.load("yamnet")(y); engine.detect_sound_event(y)',
    'genre': 'classifier.predict(y); pipeline("audio-classification")(y)',
    'separation': 'demucs.separate(y); Separator().separate_to_file(path); engine.separate_stems(y)',
    'features': 'import librosa\nlibrosa.feature.chroma_stft(y); librosa.feature.mfcc(y); librosa.feature.spectral_centroid(y); librosa.feature.zero_crossing_rate(y)',
    'pitch': 'import librosa, aubio\nlibrosa.piptrack(y); librosa.yin(y); crepe.predict(y); aubio.pitch(); sound.to_pitch(); engine.detect_pitch(y)',
    'onsets': 'import librosa\nlibrosa.onset.onset_detect(y); librosa.onset.onset_strength(y); engine.detect_onsets(y)',
    'hashing': 'hashlib.md5(data); hashlib.sha256(data)',
    'filter': 'signal.lfilter(b,a,y); equalizer.filter(y)',
    'mix': 'engine.mix_tracks(a,b)',
    'normalize': 'librosa.util.normalize(y); engine.normalize_volume(y)',
    'language': 'engine.detect_language(text)',
    'translation': 'engine.translate(text)',
    'lone_other_library': 'import madmom',
    'subprocess': 'subprocess.run(["chordino", "input.wav"])',
    'string': 'text = "essentia.ChordsDetection()"',
    'reference': 'import essentia\nessentia.ChordsDetection',
    'tempo': 'import librosa, aubio, essentia\nlibrosa.beat.beat_track(y); librosa.feature.tempo(y); aubio.tempo(); essentia.RhythmExtractor2013(); engine.detect_tempo(y)',
    'key': 'engine.detect_key(y); engine.estimate_key(y)',
    'transcription': 'basic_pitch.predict(y); mt3.transcribe(y)',
    'symbolic': 'pychord.Chord("C"); music21.chord.Chord([60,64,67])',
    'unbound': 'essentia.ChordsDetection()',
    'wrong_library': 'import other as essentia\nessentia.ChordsDetection()',
    'wrong_base': 'other.ChordsDetectionBeats()',
    'bare_name': 'detect_chords(y)',
    'nested_import': 'def setup():\n import essentia\nessentia.ChordsDetection()',
    'invalid': 'engine.detect_chords((',
    'shadow_alias': 'from engine import detect_chords as run\ndef run(y): pass\nrun(y)',
    'shadow_method': 'class Stub:\n def detect_chords(self,y): pass\nengine.detect_chords(y)',
    'shadow_async': 'async def detect_chords(y): pass\nengine.detect_chords(y)',
    'lone_chord_import': 'import pychord',
    'essentia_from': 'from essentia.standard import ChordsDetection\nChordsDetection()',
}

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(self.root)] + list(args))
        return code, out.getvalue(), err.getvalue()

    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text(encoding='utf-8'))
        values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign)}
        self.assertEqual(tuple(map(normalize, values['CHORD'])), tuple(map(normalize, EXPECTED_CHORD)))
        self.assertEqual(tuple(map(normalize, values['NOCHORD'])), tuple(map(normalize, EXPECTED_NOCHORD)))
        self.assertEqual(len(values['CHORD']), 50)
        self.assertEqual(len(values['NOCHORD']), 24)

    def test_good(self):
        self.write('README.md', 'Supports chord detection.')
        self.write('app.py', GOOD['essentia_chain'])
        self.assertEqual(self.run_cli()[0:2], (0, 'PASS\n'))

    def test_bad_exact_and_json(self):
        self.write('README.md', 'Chord detection')
        self.write('app.py', 'import librosa')
        code, out, _ = self.run_cli('--json')
        data = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(data['verdict'], 'FAIL')
        self.assertEqual(len(data['findings']), 1)
        self.assertEqual(data['findings'][0]['id'], 'documented-chord-detection-claim-false')
        self.assertEqual(data['findings'][0]['severity'], 'HIGH')
        self.assertTrue(data['findings'][0]['message'])

    def test_test_only(self):
        self.write('README.md', 'Detects chords')
        self.write('tests/helper.py', GOOD['essentia_beats'])
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli('--fail-on', 'MEDIUM')[0], 2)
        finding = audit(self.root)['findings'][0]
        self.assertEqual(finding['id'], 'documented-chord-detection-claim-false')
        self.assertEqual(finding['severity'], 'MEDIUM')

    def test_denial_exact(self):
        self.write('README.md', 'Does not detect chords')
        self.write('app.py', GOOD['essentia'])
        code, out, _ = self.run_cli('--json')
        result = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(result['findings'][0]['id'], 'documented-no-chord-detection-claim-false')
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')
        self.assertEqual(len(result['findings']), 1)

    def test_no_claim(self):
        self.write('README.md', 'An audio utility.')
        self.write('app.py', GOOD['essentia_beats'])
        self.assertEqual(audit(self.root)['verdict'], 'PASS')

    def test_no_source_asymmetry(self):
        self.write('README.md', 'Chord detection')
        self.assertEqual(self.run_cli()[0], 2)
        self.write('README.md', 'No chord detection')
        self.assertEqual(self.run_cli()[0], 0)

    def test_both_families_once(self):
        self.write('README.md', 'Detects chords.\n\nNo chord detection.')
        result = audit(self.root)
        self.assertEqual(len(result['findings']), 1)
        self.write('app.py', GOOD['essentia_beats'])
        self.assertEqual(len(audit(self.root)['findings']), 1)

    def test_fences(self):
        for marker in ('```', '~~~', '   ````'):
            with self.subTest(marker=marker):
                self.assertEqual(claims(marker + 'python\nChord detection\n' + marker), (False, False))
        self.assertEqual(claims('```\nChord detection\n~~~\n'), (False, False))
        self.assertEqual(claims('```\nclaim\n```\nChord detection'), (True, False))
        self.assertEqual(claims('    ```\nChord detection'), (True, False))

    def test_inline(self):
        self.assertEqual(claims('Supports `chord detection`.'), (True, False))

    def test_normalization_and_boundaries(self):
        self.assertEqual(claims("DOESN'T detect-chords"), (False, True))
        self.assertEqual(claims('Real-time   CHORD\n detection'), (True, False))
        self.assertEqual(claims('detects chordss'), (False, False))
        self.assertEqual(claims('chord\n\ndetection'), (False, False))
        self.assertEqual(claims('No chord detection. Also detects chords.'), (True, True))
        self.assertEqual(claims('chord detection algorithm'), (True, False))

    def test_document_selection(self):
        self.write('other.md', 'Chord detection')
        self.assertEqual(audit(self.root)['verdict'], 'PASS')
        self.write('nested/docs/more/deep.md', 'Detects chords')
        self.assertEqual(self.run_cli()[0], 2)

    def test_excluded_components(self):
        self.write('README.md', 'Chord detection')
        for directory in ('fixtures', 'docs', 'examples'):
            self.write(directory + '/impl.py', GOOD['essentia_beats'])
        self.assertFalse(audit(self.root)['production_evidence'])
        self.assertFalse(audit(self.root)['test_evidence'])

    def test_test_filename_patterns(self):
        self.write('README.md', 'Chord detection')
        for filename in ('test_impl.py', 'impl_test.py', 'nested/tests/helper.py'):
            path = self.write(filename, GOOD['essentia_beats'])
            result = audit(self.root)
            self.assertTrue(result['test_evidence'])
            self.assertFalse(result['production_evidence'])
            path.unlink()

    def test_symlinks(self):
        self.write('README.md', 'Chord detection')
        excluded = self.write('fixtures/real.py', GOOD['essentia_beats'])
        (self.root / 'linked.py').symlink_to(excluded)
        (self.root / 'linked_dir').symlink_to(excluded.parent, target_is_directory=True)
        self.assertEqual(self.run_cli()[0], 2)
        self.write('README.md', 'Unrelated prose')
        doc = self.write('fixtures/claim.txt', 'Chord detection')
        (self.root / 'docs').mkdir()
        (self.root / 'docs/linked.md').symlink_to(doc)
        self.assertEqual(self.run_cli()[0], 0)

    def test_single_module_scope(self):
        self.write('README.md', 'Chord detection')
        self.write('imports.py', 'import essentia\nfrom engine import detect_chords')
        self.write('calls.py', 'essentia.ChordsDetection(); detect_chords(y)')
        self.assertEqual(self.run_cli()[0], 2)

    def test_ignore_repeatable_prefix(self):
        self.write('README.md', 'Chord detection')
        self.write('one/app.py', GOOD['essentia_beats'])
        self.write('two/app.py', GOOD['essentia_beats'])
        self.assertEqual(self.run_cli('--ignore', 'one', '--ignore', 'two')[0], 2)
        self.assertEqual(self.run_cli('--ignore', 'on')[0], 0)
        self.assertEqual(self.run_cli('--ignore', 'README.md')[0], 0)

    def test_verbose(self):
        self.write('README.md', 'Utility')
        self.assertIn('README.md', self.run_cli('--verbose')[1])

    def test_usage_errors(self):
        for args in ([], ['--unknown'], ['--fail-on', 'INVALID', str(self.root)]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(args)
                self.assertEqual(raised.exception.code, 1)
        self.assertEqual(self.run_cli('--ignore', 'x')[0], 0)

    def test_io_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.root / 'missing')]), 1)
        self.write('README.md', '\udcff'.encode('utf-8', errors='surrogateescape').decode('latin1'))
        (self.root / 'README.md').write_bytes(b'\xff')
        self.assertEqual(self.run_cli()[0], 1)

    def test_version_and_module_entry(self):
        result = subprocess.run([sys.executable, '-m', 'chord_detection_claim_audit', '--version'],
                                capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, '0.1.0'))
        self.assertEqual(__version__, '0.1.0')
        self.write('README.md', 'Chord detection')
        result = subprocess.run([sys.executable, '-m', 'chord_detection_claim_audit', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_entry_point_configuration(self):
        config = (Path(__file__).resolve().parents[1] / 'pyproject.toml').read_text()
        self.assertIn('chord-detection-claim-audit = "chord_detection_claim_audit.audit:main"', config)

    def test_readme_self_audit(self):
        readme = Path(__file__).resolve().parents[1] / 'README.md'
        self.assertEqual(readme.read_text().splitlines()[0], '# Documentation claim auditor')
        self.assertEqual(claims(readme.read_text()), (False, False))
        self.write('README.md', readme.read_text())
        self.assertEqual(audit(self.root)['verdict'], 'PASS')


def _evidence_test(source, expected):
    def check(self):
        self.assertIs(evidence(source), expected)
        self.write('README.md', 'Chord detection')
        self.write('app.py', source)
        self.assertEqual(self.run_cli()[0], 0 if expected else 2)
    return check


for _name, _source in GOOD.items():
    setattr(AuditTests, 'test_route_' + _name, _evidence_test(_source, True))
for _name, _source in BAD.items():
    setattr(AuditTests, 'test_not_evidence_' + _name, _evidence_test(_source, False))
for _name in GENERIC_NAMES:
    setattr(AuditTests, 'test_generic_attribute_' + _name,
            _evidence_test('engine.' + _name + '(audio)', True))
    setattr(AuditTests, 'test_generic_import_' + _name,
            _evidence_test('from engine import ' + _name + '\n' + _name + '(audio)', True))
    setattr(AuditTests, 'test_generic_alias_' + _name,
            _evidence_test('from engine import ' + _name + ' as run\nrun(audio)', True))
    setattr(AuditTests, 'test_generic_shadow_' + _name,
            _evidence_test('def ' + _name + '(y): pass\nengine.' + _name + '(audio)', False))

for _index, _phrase in enumerate(EXPECTED_CHORD):
    def _positive(self, phrase=_phrase):
        self.assertEqual(claims(phrase), (True, False))
    setattr(AuditTests, 'test_positive_phrase_%02d' % _index, _positive)
for _index, _phrase in enumerate(EXPECTED_NOCHORD):
    def _negative(self, phrase=_phrase):
        self.assertEqual(claims(phrase), (False, True))
    setattr(AuditTests, 'test_negative_phrase_%02d' % _index, _negative)


if __name__ == '__main__':
    unittest.main()
