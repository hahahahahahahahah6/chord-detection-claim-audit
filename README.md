# Documentation claim auditor

An offline audit tool that compares documentation statements with static
Python call evidence. It reads source as syntax and never executes the
inspected project. It makes no network requests, writes no files, and collects
no telemetry.

Requires Python 3.9 or later. Install from either distribution:

```sh
python3 -m pip install chord_detection_claim_audit-0.1.0-py3-none-any.whl
python3 -m pip install chord_detection_claim_audit-0.1.0.tar.gz
```

Run either entry point against a directory:

```sh
chord-detection-claim-audit ./project
python3 -m chord_detection_claim_audit ./project --json
python3 -m chord_detection_claim_audit ./project --verbose --ignore vendor --ignore build
python3 -m chord_detection_claim_audit ./project --fail-on MEDIUM
python3 -m chord_detection_claim_audit --version
```

The audit reads the root README and Markdown files below any directory component
named `docs`. Fenced code is excluded; inline code counts. Paragraph matching
ignores case, expands negative contractions, replaces hyphens with spaces, and
collapses whitespace. Exact phrases use word boundaries. Longer phrases take
precedence, with alphabetical ties. Negative spans are removed before affirmative
matching.

Python evidence must be complete within one module. Supported syntax includes
library calls, imported aliases, and the specific generic method names in the
package vocabulary:

```text
essentia: ChordsDetection, ChordsDetectionBeats (including attribute chains)
generic: analyse_chords, analyze_chords, chord_detect, chord_identify, chord_label, chord_predict, chord_recognition, chord_track, classify_chords, detect_chord, detect_chord_progression, detect_chords, estimate_chord, estimate_chord_progression, estimate_chords, extract_chords, get_chord, get_chords, identify_chords, label_chords, predict_chords, recognise_chords, recognize_chords, track_chord_progression, track_chords
```

Imports alone, strings, bare references, subprocess commands, invalid syntax,
and adjacent audio operations do not establish evidence. Generic calls require
an attribute or a resolved from-import; local function and method definitions
shadow these names. Library routes use their own binding conditions.

Symlinks are skipped. Files inside `fixtures`, `docs`, and `examples` do not
supply evidence. Files inside `tests`, or with conventional test filenames,
supply only test evidence. An affirmative statement without production evidence
produces one finding; test evidence lowers its severity. A negative statement
with production evidence produces one finding. With no Python files, an
unsupported affirmative statement still produces a finding; a negative one passes.

```text
documented-chord-detection-claim-false       HIGH (MEDIUM with test evidence only)
documented-no-chord-detection-claim-false    HIGH
```

JSON includes `verdict`, `findings`, inspected document and source paths, and
production and test evidence flags. Every finding includes `id`, `severity`,
and `message`. The verdict is `FAIL` whenever findings exist, even when they
fall below the exit threshold. The default threshold is `HIGH`; `--fail-on`
accepts `LOW`, `MEDIUM`, or `HIGH`. Exit status is 0 below the threshold,
2 at or above it, and 1 for usage or I/O errors. `--ignore` is repeatable and
excludes relative path prefixes at path component boundaries.

This is a static heuristic: a recognized call does not prove that an operation
works at runtime, and alternative implementations may be unrecognized.

Run the test suite and build isolated distributions:

```sh
python3 -m pip install build
python3 -m unittest discover
python3 -m build
```

MIT licensed.
