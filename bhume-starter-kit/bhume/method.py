"""A simple but better-than-global baseline method.

This kit is about the *method*: where/how you apply local corrections, and how you
translate image/raster evidence into geometry + confidence.

This starter implementation is intentionally conservative:
- If `boundaries.tif` exists, it uses it to estimate a local translation for each plot.
- Otherwise, it falls back to `global_median_shift`.
- It can also choose to `flagged` plots when the local signal is weak.

The code focuses on correctness of plumbing + output schema. Geometry heuristics are
kept lightweight so it runs fast on CPU.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.affinity import translate
from shapely.geometry import shape

from bhume.baseline import global_median_shift
from bhume.geo import geom_to_imagery_crs


@dataclass
class LocalTranslation:
    dx_m: float
    dy_m: float
    score: float  # higher = stronger evidence


def _read_boundary_raster(boundaries_path: str):
    """Open a boundaries raster and return dataset (context-managed outside)."""
    return rasterio.open(boundaries_path)


def _estimate_translation_from_boundaries(
    src_boundaries,
    plot_geom_4326,
) -> LocalTranslation:
    """Estimate a translation by comparing rasters under the plot.

    Heuristic:
    - Take the plot polygon, reproject into the boundaries raster CRS (imagery CRS).
    - Crop a mask of boundary pixels within that polygon buffer.
    - Compute the centroid of boundary pixels in pixel coordinates, then convert to
      metres using the raster transform (assumes roughly uniform square pixels).

    This yields a translation target relative to the plot centroid (in the same CRS).

    Note: This is a deliberately simple estimator. The assignment expects you to replace
    it with a stronger approach.
    """
    # boundaries raster is in imagery CRS (EPSG:3857) for this starter kit.
    # We work in that CRS to get metres.
    plot_g = geom_to_imagery_crs(src_boundaries, plot_geom_4326)

    minx, miny, maxx, maxy = plot_g.bounds
    pad = 30.0  # metres
    minx -= pad
    miny -= pad
    maxx += pad
    maxy += pad

    # Crop window in raster coordinates
    window = rasterio.windows.from_bounds(minx, miny, maxx, maxy, transform=src_boundaries.transform)
    window = window.round_offsets().round_lengths()

    data = src_boundaries.read(1, window=window)

    # Build coordinate grid for pixels to compute centroid in CRS.
    # data is (H, W). We'll use affine to map pixel centers.
    h, w = data.shape
    if h == 0 or w == 0:
        return LocalTranslation(0.0, 0.0, score=0.0)

    # Assume boundary raster uses non-zero as boundary evidence.
    mask = data != 0
    n = int(mask.sum())
    if n < 10:
        return LocalTranslation(0.0, 0.0, score=0.0)

    # Pixel indices of boundary pixels
    ys, xs = np.nonzero(mask)

    # Convert local pixel coords to global CRS coords using dataset transform.
    # Pixel center: x = col + 0.5, y = row + 0.5.
    cols = xs + window.col_off + 0.5
    rows = ys + window.row_off + 0.5

    # rasterio.transform.xy: offset can be 'center'/'ul'/'ur'/'ll'/'lr' or 0/0.5; 
    # use 'center' to avoid Invalid offset errors.
    xs_crs, ys_crs = rasterio.transform.xy(src_boundaries.transform, rows, cols, offset='center')
    xs_crs = np.asarray(xs_crs, dtype=float)
    ys_crs = np.asarray(ys_crs, dtype=float)


    boundary_cx = float(xs_crs.mean())
    boundary_cy = float(ys_crs.mean())

    plot_cent = plot_g.centroid
    dx = boundary_cx - plot_cent.x
    dy = boundary_cy - plot_cent.y

    # Evidence score: boundary pixel count normalized by patch area.
    patch_area_m2 = max((maxx - minx) * (maxy - miny), 1e-9)
    score = min(1.0, n / (patch_area_m2 / (src_boundaries.res[0] * src_boundaries.res[1]) + 1e-9))

    return LocalTranslation(dx_m=dx, dy_m=dy, score=score)


def predict_boundaries(
    village,
    *,
    confidence_threshold: float = 0.25,
    fallback_confidence: float = 0.4,
) -> gpd.GeoDataFrame:
    """Predict corrected/flagged plot boundaries for a whole village.

    Returns a GeoDataFrame indexed by plot_number (not required), with columns matching the
    contract writer: plot_number, status, confidence, method_note, geometry.
    """
    # Fallback baseline in case we don't have boundary hints.
    if village.boundaries_path is None:
        return global_median_shift(village, confidence=fallback_confidence)

    preds = []
    official = village.plots

    # Keep CRS alignment simple: plot geometries are in EPSG:4326.
    # Our boundary raster heuristic works in the raster CRS (imagery CRS), returning dx/dy in metres.
    with _read_boundary_raster(str(village.boundaries_path)) as bsrc:
        for pn, row in official.iterrows():
            geom = row.geometry
            lt = _estimate_translation_from_boundaries(bsrc, geom)

            if lt.score < confidence_threshold:
                preds.append(
                    {
                        "plot_number": str(pn),
                        "status": "flagged",
                        "confidence": np.nan,
                        "method_note": f"weak boundary signal (score={lt.score:.2f}); kept official",
                        "geometry": geom,
                    }
                )
                continue

            moved = translate(geom, lt.dx_m, lt.dy_m)
            preds.append(
                {
                    "plot_number": str(pn),
                    "status": "corrected",
                    "confidence": float(min(1.0, max(0.0, 0.3 + 0.7 * lt.score))),
                    "method_note": f"translated by dx={lt.dx_m:.1f}m dy={lt.dy_m:.1f}m using boundaries.tif",
                    "geometry": moved,
                }
            )

    gdf = gpd.GeoDataFrame(preds, geometry="geometry", crs="EPSG:4326")

    # Ensure schema compatibility: writer only selects columns it finds.
    return gdf[[c for c in ("plot_number", "status", "confidence", "method_note", "geometry") if c in gdf.columns]]

