# TODO - @bhume-starter-kit/

## Step 1: Gather & confirm requirements
- [x] Read repo modules: `bhume/io.py`, `bhume/geo.py`, `bhume/baseline.py`, `bhume/score.py`, `README.md`, `CONTRACT.md`, `quickstart.py`, `bhume/__init__.py`.
- [x] Proposed edit plan to add improved method + integrate into quickstart.
- [x] Got approval: implement `bhume/method.py` and update `quickstart.py`; use `boundaries.tif` when available.

## Step 2: Implement improved correction method
- [ ] Create `bhume/method.py`
- [ ] Implement `predict_boundaries(village, ...)` returning GeoDataFrame with `plot_number`, `status`, `confidence`, `method_note`, `geometry`
- [ ] Use `boundaries.tif` when available as a hint; otherwise fall back to imagery-only heuristic

## Step 3: Integrate into runner
- [ ] Update `quickstart.py` to use the new method (baseline still shown for comparison)
- [ ] Optionally export in `bhume/__init__.py`

## Step 4: Sanity checks
- [ ] Run `uv sync`
- [ ] Run `uv run quickstart.py data/<village>`
- [ ] Ensure output `predictions.geojson` is written and `score()` runs
- [ ] Address any schema/CRS/geometry validity issues

