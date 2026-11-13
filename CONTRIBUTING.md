# Contributing

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and replay the public
demo into a fresh run directory before proposing a change.

Keep private transcripts, screenshots, credentials, and generated run directories
out of commits. Use invented fixtures that clearly state they are synthetic.

Changes to importers should include branch, duplication, source-role, malformed
input, and completeness cases. Changes to attribution or recommendations need
negative examples as well as useful cases. Never make an empty findings list fail
just because it is empty, or call citation validation proof of semantic accuracy.

If an input format is unsupported, preserve an explicit limitation rather than
silently guessing a canonical branch or labeling generated text as human evidence.

Report changes should preserve offline operation, HTML escaping, mobile reading,
keyboard-accessible evidence disclosures, reduced-motion behavior, and printing.
Keep SVGs local and retain their upstream license notice. Validate visual changes
with a freshly generated synthetic report at desktop and mobile sizes.

Keep the English and Chinese READMEs, architecture notes, and analysis contract
aligned with the implementation. Reader-facing suggestions describe reasoning
directions in a collegial tone; see the Skill's report style contract.
