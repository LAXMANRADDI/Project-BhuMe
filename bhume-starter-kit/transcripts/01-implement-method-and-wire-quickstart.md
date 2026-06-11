# 01 - Implement predict_boundaries using boundaries.tif and wire into quickstart

## Goal
Add an improved per-plot boundary correction method beyond `global_median_shift`, and integrate it into the runnable example.

## Work performed
1. Inspected existing helpers
   - `bhume/io.py` (load / write_predictions contract)
   - `bhume/geo.py` (CRS handling, patch extraction)
   - `bhume/baseline.py` (global shift)
   - `bhume/score.py` (self-scoring)
   - `quickstart.py` (end-to-end loop)
2. Implemented new method
   - Created `bhume/method.py` with:
     - `predict_boundaries(village, confidence_threshold=0.25, fallback_confidence=0.4)`
     - If `village.boundaries_path` exists:
       - For each plot, estimate a local translation from `boundaries.tif`
       - If evidence score is weak: output `status='flagged'` and keep official geometry
       - Otherwise: output `status='corrected'` with a confidence derived from evidence score
     - If `boundaries.tif` is missing:
       - Fall back to `global_median_shift`
   - Ensured output schema compatibility with `write_predictions()`:
     - `plot_number`, `status`, `confidence` (only for corrected), `method_note`, `geometry`
3. Wired method into runner
   - Updated `quickstart.py`:
     - Runs `predict_boundaries(village)` and writes `predictions.geojson`
     - Still prints baseline `global_median_shift` score when `example_truths.geojson` is present
     - Removed a unicode arrow `→` to avoid Windows console encoding issues
4. Exported for convenience
   - Updated `bhume/__init__.py` to export `predict_boundaries`

## Validation
- Created a local bundle `data/1bundle` from the provided example files (1/2 prefixes in workspace).
- Ran:
  - `uv run python quickstart.py data/1bundle`
- Observed:
  - `data/1bundle/predictions.geojson` gets written.
  - Scoring runs; in the small example bundle this method flagged all plots (so IoU/confidence aggregates were not available).

## Files changed
- `bhume/method.py` (added)
- `quickstart.py` (updated)
- `bhume/__init__.py` (updated)
- `transcripts/README.md` (added)
- `transcripts/01-implement-method-and-wire-quickstart.md` (added)

