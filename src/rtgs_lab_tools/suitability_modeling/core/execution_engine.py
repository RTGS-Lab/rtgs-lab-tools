"""Execution engine for suitability models."""

import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
except ImportError:
    gpd = None


def execute_model(
    model_spec: "ModelSpecification",
    datasets: Dict[str, "gpd.GeoDataFrame"],
    study_area_boundary: "gpd.GeoDataFrame",
    analysis_units: Optional["gpd.GeoDataFrame"] = None,
    output_dir: str = "./results",
    output_format: str = "geoparquet",
    id_column: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a suitability model with pre-loaded data.

    Args:
        model_spec: ModelSpecification object or path to YAML file
        datasets: Dict mapping dataset names to GeoDataFrames
        study_area_boundary: GeoDataFrame with study area boundary
        analysis_units: Optional pre-built analysis units (grid or features).
            If None, will be generated from model_spec.analysis_units_config.
        output_dir: Directory to save results
        output_format: Output format (geoparquet, shapefile, geojson, csv)
        id_column: Optional column name to keep as identifier in output.
            If set, output will only contain this column, geometry, and scores.

    Returns:
        Dict with execution results and output file path
    """
    if gpd is None:
        raise ImportError("geopandas required. Install with: pip install geopandas")

    from .model_specification import ModelSpecification

    # Handle YAML file path input
    if isinstance(model_spec, str):
        logger.info(f"Loading model specification from: {model_spec}")
        model_spec = ModelSpecification.from_yaml(model_spec)

    logger.info(f"Executing model: {model_spec.model_id}")
    start_time = datetime.now()

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Execute the model
    engine = SuitabilityEngine(model_spec, datasets, study_area_boundary, analysis_units)
    results_gdf = engine.execute(id_column=id_column)

    # Export results
    output_file = engine.export_results(results_gdf, output_dir, output_format)

    # Save model YAML alongside results
    model_yaml_path = output_path / f"{model_spec.model_id}.yaml"
    model_spec.to_yaml(str(model_yaml_path))

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"Model execution complete in {duration:.1f} seconds")

    return {
        "success": True,
        "model_id": model_spec.model_id,
        "output_file": output_file,
        "model_yaml": str(model_yaml_path),
        "num_features": len(results_gdf),
        "duration_seconds": duration,
        "timestamp": end_time.isoformat(),
    }


class SuitabilityEngine:
    """Engine for executing weighted overlay suitability models."""

    def __init__(
        self,
        model_spec: "ModelSpecification",
        datasets: Dict[str, "gpd.GeoDataFrame"],
        study_area_boundary: "gpd.GeoDataFrame",
        analysis_units: Optional["gpd.GeoDataFrame"] = None,
    ):
        """Initialize engine with model specification and pre-loaded data.

        Args:
            model_spec: ModelSpecification object
            datasets: Dict mapping dataset names to GeoDataFrames
            study_area_boundary: GeoDataFrame with study area boundary
            analysis_units: Optional pre-built analysis units
        """
        self.model_spec = model_spec
        self.datasets = datasets
        self.study_area_boundary = study_area_boundary
        self.analysis_units = analysis_units

    def execute(self, id_column: Optional[str] = None) -> gpd.GeoDataFrame:
        """Execute the suitability model.

        Args:
            id_column: Optional column name to keep as identifier in output.
                If set, output will only contain this column, geometry, and scores.

        Returns:
            GeoDataFrame with suitability scores
        """
        # Clip datasets to study area boundary
        logger.info("Clipping datasets to study area boundary...")
        self._clip_datasets_to_boundary()

        # Create or use analysis units
        logger.info("Preparing analysis units...")
        study_area = self._prepare_analysis_units()

        # Build a mapping from criterion_name to dataset_name for column naming
        criterion_dataset_map = {}
        for criterion in self.model_spec.criteria:
            criterion_dataset_map[criterion.criterion_name] = criterion.dataset_name

        logger.info("Calculating criterion scores...")
        criterion_scores = {}
        for criterion in self.model_spec.criteria:
            scores = self._calculate_criterion_score(study_area, criterion)
            criterion_scores[criterion.criterion_name] = scores

        logger.info("Combining scores with weights...")
        final_scores = self._combine_scores(criterion_scores)

        # Rescale to output range
        min_score, max_score = self.model_spec.output_range
        final_scores = min_score + (final_scores / 10.0) * (max_score - min_score)

        # Build clean output columns
        score_columns = {}
        score_columns["suitability_score"] = final_scores

        # Use dataset names for individual score columns
        for criterion_name, scores in criterion_scores.items():
            dataset_name = criterion_dataset_map[criterion_name]
            col_name = f"score_{dataset_name}"
            score_columns[col_name] = scores

        # Build output GeoDataFrame
        if id_column and id_column in study_area.columns:
            output = study_area[[id_column, study_area.geometry.name]].copy()
        else:
            output = study_area[[study_area.geometry.name]].copy()

        for col_name, values in score_columns.items():
            output[col_name] = values

        logger.info(f"Analysis complete. Mean suitability: {final_scores.mean():.2f}")

        return output

    def _clip_datasets_to_boundary(self) -> None:
        """Clip all loaded datasets to the study area boundary."""
        if self.study_area_boundary is None or self.study_area_boundary.empty:
            return

        boundary_geom = self.study_area_boundary.unary_union

        for name, gdf in self.datasets.items():
            if gdf.empty:
                continue

            original_count = len(gdf)

            # Ensure same CRS
            if gdf.crs != self.study_area_boundary.crs:
                gdf = gdf.to_crs(self.study_area_boundary.crs)

            gdf = gdf[gdf.intersects(boundary_geom)]
            self.datasets[name] = gdf

            logger.info(f"  {name}: {original_count} -> {len(gdf)} features")

    def _prepare_analysis_units(self) -> gpd.GeoDataFrame:
        """Create or return analysis units.

        Returns:
            GeoDataFrame with analysis units
        """
        if self.analysis_units is not None:
            logger.info(f"  Using provided analysis units: {len(self.analysis_units)} features")
            return self.analysis_units.copy()

        analysis_config = self.model_spec.analysis_units_config

        if analysis_config is None or analysis_config.type == "grid":
            return self._create_grid_units()
        elif analysis_config.type in ["parcels", "cities", "dataset"]:
            return self._load_analysis_units_from_dataset(analysis_config)
        else:
            raise ValueError(f"Unsupported analysis unit type: {analysis_config.type}")

    def _create_grid_units(self) -> gpd.GeoDataFrame:
        """Create regular grid cells using spatial_data.generate_grid().

        Returns:
            GeoDataFrame with grid cells
        """
        from ...spatial_data.core.grid import generate_grid

        analysis_config = self.model_spec.analysis_units_config
        cell_size = analysis_config.cell_size if analysis_config else 100.0
        max_cells = analysis_config.max_cells if analysis_config else 10000

        grid = generate_grid(
            boundary=self.study_area_boundary,
            cell_size=cell_size,
            max_cells=max_cells,
        )

        logger.info(f"  Generated grid: {len(grid)} cells ({cell_size}m)")
        return grid

    def _load_analysis_units_from_dataset(self, analysis_config) -> gpd.GeoDataFrame:
        """Load analysis units from a dataset (parcels, cities, etc.).

        Args:
            analysis_config: AnalysisUnitsConfig with dataset name

        Returns:
            GeoDataFrame with analysis units
        """
        dataset_name = analysis_config.dataset
        if not dataset_name:
            raise ValueError(
                f"Analysis unit type '{analysis_config.type}' requires a dataset name"
            )

        if dataset_name not in self.datasets:
            raise ValueError(
                f"Analysis units dataset '{dataset_name}' not found in loaded datasets"
            )

        units_gdf = self.datasets[dataset_name].copy()

        # Clip to boundary
        if self.study_area_boundary is not None and not self.study_area_boundary.empty:
            boundary_geom = self.study_area_boundary.unary_union
            if units_gdf.crs != self.study_area_boundary.crs:
                units_gdf = units_gdf.to_crs(self.study_area_boundary.crs)
            units_gdf = units_gdf[units_gdf.intersects(boundary_geom)].copy()
            units_gdf.geometry = units_gdf.geometry.intersection(boundary_geom)
            units_gdf = units_gdf[~units_gdf.geometry.is_empty]

        # Limit number of units
        max_cells = analysis_config.max_cells
        if len(units_gdf) > max_cells:
            logger.warning(
                f"Dataset has {len(units_gdf)} units, limiting to {max_cells}"
            )
            units_gdf = units_gdf.sample(n=max_cells, random_state=42)

        logger.info(f"  Using {len(units_gdf)} analysis units from {dataset_name}")
        return units_gdf

    def _calculate_criterion_score(
        self, study_area: gpd.GeoDataFrame, criterion: "ModelCriterion"
    ) -> np.ndarray:
        """Calculate suitability score for a single criterion.

        Args:
            study_area: GeoDataFrame with analysis units
            criterion: ModelCriterion to score

        Returns:
            Array of scores (0-10 scale)
        """
        dataset = self.datasets[criterion.dataset_name]
        scoring_func = criterion.scoring_function

        logger.info(f"  Scoring: {criterion.criterion_name}")

        if scoring_func.type == "distance_decay":
            scores = self._score_distance_decay(study_area, dataset, scoring_func)
        elif scoring_func.type == "categorical":
            scores = self._score_categorical(study_area, dataset, scoring_func)
        elif scoring_func.type == "direct_value":
            scores = self._score_direct_value(study_area, dataset, scoring_func)
        else:
            raise ValueError(f"Unsupported scoring function: {scoring_func.type}")

        logger.info(f"    Score range: {scores.min():.2f} - {scores.max():.2f}")
        return scores

    def _score_distance_decay(
        self,
        study_area: gpd.GeoDataFrame,
        features: gpd.GeoDataFrame,
        scoring_func: "ScoringFunction",
    ) -> np.ndarray:
        """Score based on distance to features with exponential decay.

        Args:
            study_area: Analysis units
            features: Features to calculate distance from
            scoring_func: Scoring function with parameters

        Returns:
            Array of scores (0-10)
        """
        params = scoring_func.params
        max_distance = params.get("max_distance", 2000)
        decay_rate = params.get("decay_rate", 0.001)

        # Reproject to projected CRS for accurate distance calculations
        if study_area.crs and study_area.crs.is_geographic:
            target_crs = "EPSG:5070"
            study_area_proj = study_area.to_crs(target_crs)
            features_proj = features.to_crs(target_crs)
        else:
            study_area_proj = study_area
            features_proj = features

        # Calculate distance from each cell to nearest feature
        distances = study_area_proj.geometry.apply(
            lambda geom: features_proj.distance(geom).min()
        )

        # Apply exponential decay
        scores = 10 * np.exp(-decay_rate * distances)

        # Cap at max_distance
        scores[distances > max_distance] = 0

        return scores.values

    def _score_categorical(
        self,
        study_area: gpd.GeoDataFrame,
        features: gpd.GeoDataFrame,
        scoring_func: "ScoringFunction",
    ) -> np.ndarray:
        """Score based on categorical attributes.

        Args:
            study_area: Analysis units
            features: Features with categorical attributes
            scoring_func: Scoring function with category mapping

        Returns:
            Array of scores (0-10)
        """
        params = scoring_func.params
        mapping = params.get("mapping", {})
        category_column = params.get("column", "category")

        # Spatial join to get category for each analysis unit
        joined = gpd.sjoin(study_area, features, how="left", predicate="intersects")

        # Map categories to scores
        if category_column in joined.columns:
            scores = joined[category_column].map(mapping).fillna(0)
        else:
            logger.warning(
                f"Column '{category_column}' not found, using default score of 5"
            )
            scores = pd.Series(np.full(len(joined), 5.0), index=joined.index)

        # sjoin may produce duplicate rows when a unit overlaps multiple features.
        # Group by original index and take the max score per unit.
        import pandas as pd

        scores = scores.groupby(scores.index).max().reindex(study_area.index, fill_value=0)

        return np.asarray(scores)

    def _score_direct_value(
        self,
        study_area: gpd.GeoDataFrame,
        features: gpd.GeoDataFrame,
        scoring_func: "ScoringFunction",
    ) -> np.ndarray:
        """Score by reading a numeric column value directly via spatial join.

        Uses the actual column values as scores without remapping.

        Args:
            study_area: Analysis units
            features: Features with numeric score column
            scoring_func: Scoring function with column parameter

        Returns:
            Array of scores
        """
        import pandas as pd

        params = scoring_func.params
        column = params.get("column", None)

        if column is None:
            raise ValueError("direct_value scoring requires a 'column' parameter")

        # Spatial join to get values for each analysis unit
        joined = gpd.sjoin(study_area, features, how="left", predicate="intersects")

        if column not in joined.columns:
            logger.warning(
                f"Column '{column}' not found, using default score of 0"
            )
            return np.zeros(len(study_area))

        scores = pd.to_numeric(joined[column], errors="coerce").fillna(0)

        # sjoin may produce duplicate rows; take the max per unit
        scores = scores.groupby(scores.index).max().reindex(study_area.index, fill_value=0)

        return np.asarray(scores)

    def _combine_scores(self, criterion_scores: Dict[str, np.ndarray]) -> np.ndarray:
        """Combine criterion scores using weighted sum.

        Args:
            criterion_scores: Dict of criterion_name: score_array

        Returns:
            Array of combined scores (0-10 scale)
        """
        num_cells = len(next(iter(criterion_scores.values())))
        final_scores = np.zeros(num_cells)

        for criterion in self.model_spec.criteria:
            scores = criterion_scores[criterion.criterion_name]
            weight = criterion.weight / 100.0
            final_scores += scores * weight

        return final_scores

    def export_results(
        self, results_gdf: gpd.GeoDataFrame, output_dir: str, output_format: str
    ) -> str:
        """Export results to file.

        Args:
            results_gdf: GeoDataFrame with suitability scores
            output_dir: Output directory
            output_format: Format (geoparquet, shapefile, geojson, csv)

        Returns:
            Path to output file
        """
        output_path = Path(output_dir)
        filename = f"{self.model_spec.model_id}_results"

        if output_format == "geoparquet":
            file_path = output_path / f"{filename}.parquet"
            results_gdf.to_parquet(file_path)
        elif output_format == "shapefile":
            file_path = output_path / f"{filename}.shp"
            results_gdf.to_file(file_path, driver="ESRI Shapefile")
        elif output_format == "geojson":
            file_path = output_path / f"{filename}.geojson"
            results_gdf.to_file(file_path, driver="GeoJSON")
        elif output_format == "csv":
            file_path = output_path / f"{filename}.csv"
            results_csv = results_gdf.copy()
            results_csv["geometry"] = results_csv["geometry"].apply(lambda x: x.wkt)
            results_csv.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        logger.info(f"Results exported to: {file_path}")
        return str(file_path)
