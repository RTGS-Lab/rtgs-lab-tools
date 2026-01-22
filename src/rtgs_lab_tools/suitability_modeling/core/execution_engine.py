"""Execution engine for suitability models."""

import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import geopandas with error handling
try:
    import geopandas as gpd
except ImportError:
    gpd = None


def execute_model(
    model_spec: "ModelSpecification",
    output_dir: str = "./results",
    output_format: str = "geoparquet",
    db_url: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a suitability model and generate results.

    This function:
    1. Loads required datasets from PostGIS or spatial_data module
    2. Creates a study area grid for analysis
    3. Calculates scores for each criterion
    4. Combines scores using weighted overlay
    5. Exports results to file

    Args:
        model_spec: ModelSpecification object or path to YAML file
        output_dir: Directory to save results
        output_format: Output format (geoparquet, shapefile, geojson, csv)
        db_url: Optional PostGIS database URL (uses env config if None)

    Returns:
        Dict with execution results and output file path

    Example:
        >>> from core.model_specification import ModelSpecification
        >>> spec = ModelSpecification.from_yaml("model.yaml")
        >>> results = execute_model(spec)
        >>> print(f"Results saved to: {results['output_file']}")
    """
    if gpd is None:
        raise ImportError("geopandas required. Install with: pip install geopandas")

    # Handle both ModelSpecification objects and file paths
    from .model_specification import ModelSpecification
    if isinstance(model_spec, str):
        logger.info(f"Loading model specification from: {model_spec}")
        model_spec = ModelSpecification.from_yaml(model_spec)

    logger.info(f"Executing model: {model_spec.model_id}")
    start_time = datetime.now()

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Execute the model
    engine = SuitabilityEngine(model_spec, db_url=db_url)
    results_gdf = engine.execute()

    # Export results
    output_file = engine.export_results(
        results_gdf,
        output_dir,
        output_format
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"✓ Model execution complete in {duration:.1f} seconds")

    return {
        "success": True,
        "model_id": model_spec.model_id,
        "output_file": output_file,
        "num_features": len(results_gdf),
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }


class SuitabilityEngine:
    """Engine for executing weighted overlay suitability models."""

    def __init__(self, model_spec: "ModelSpecification", db_url: Optional[str] = None):
        """Initialize engine with model specification.

        Args:
            model_spec: ModelSpecification object
            db_url: Optional PostGIS database URL
        """
        self.model_spec = model_spec
        self.db_url = db_url
        self.datasets = {}
        self._postgis_manager = None

    def execute(self) -> gpd.GeoDataFrame:
        """Execute the suitability model.

        Returns:
            GeoDataFrame with suitability scores
        """
        logger.info("Loading study area boundary...")
        study_area_boundary = self._load_study_area_boundary()

        logger.info("Loading required datasets...")
        self._load_datasets(study_area_boundary)

        logger.info("Creating analysis units...")
        study_area = self._create_study_area(study_area_boundary)

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

        # Add to study area
        study_area['suitability_score'] = final_scores

        # Add individual criterion scores for transparency
        for name, scores in criterion_scores.items():
            col_name = f"score_{name.lower().replace(' ', '_')}"
            study_area[col_name] = scores

        logger.info(f"✓ Analysis complete. Mean suitability: {final_scores.mean():.2f}")

        return study_area

    def _load_study_area_boundary(self) -> Optional[gpd.GeoDataFrame]:
        """Load study area boundary if specified in model config.

        Returns:
            GeoDataFrame with boundary geometry, or None if not specified
        """
        if not self.model_spec.study_area_config or not self.model_spec.study_area_config.dataset:
            logger.info("  No study area boundary specified")
            return None

        boundary_dataset = self.model_spec.study_area_config.dataset
        logger.info(f"  Loading boundary: {boundary_dataset}")

        # Load boundary from PostGIS (boundaries should be in database)
        from .dataset_registry import get_dataset_source
        source = get_dataset_source(boundary_dataset, db_url=self.db_url)

        if source == 'postgis':
            boundary_gdf = self._load_from_postgis(boundary_dataset)
        elif source == 'spatial_data':
            boundary_gdf = self._load_from_spatial_data(boundary_dataset)
        else:
            raise ValueError(f"Study area boundary '{boundary_dataset}' not found")

        logger.info(f"    Loaded boundary with {len(boundary_gdf)} features")
        return boundary_gdf

    def _load_datasets(self, study_area_boundary: Optional[gpd.GeoDataFrame] = None):
        """Load required datasets from PostGIS or spatial_data module.

        Args:
            study_area_boundary: Optional boundary to clip datasets to
        """
        from .dataset_registry import get_dataset_source

        for criterion in self.model_spec.criteria:
            dataset_name = criterion.dataset_name

            if dataset_name in self.datasets:
                continue  # Already loaded

            logger.info(f"  Loading dataset: {dataset_name}")

            # Determine where dataset comes from
            source = get_dataset_source(dataset_name, db_url=self.db_url)
            logger.info(f"    Source: {source}")

            try:
                if source == 'postgis':
                    # Load from PostGIS database
                    gdf = self._load_from_postgis(dataset_name)
                elif source == 'spatial_data':
                    # Load from spatial_data module
                    gdf = self._load_from_spatial_data(dataset_name)
                else:
                    raise ValueError(
                        f"Dataset '{dataset_name}' not found in PostGIS or spatial_data. "
                        f"Source: {source}"
                    )

                # Clip to study area boundary if specified
                if study_area_boundary is not None and not study_area_boundary.empty:
                    logger.info(f"    Clipping to study area boundary...")
                    original_count = len(gdf)

                    # Ensure same CRS
                    if gdf.crs != study_area_boundary.crs:
                        gdf = gdf.to_crs(study_area_boundary.crs)

                    # Create union of boundary geometries
                    boundary_geom = study_area_boundary.unary_union

                    # Clip features to boundary
                    gdf = gdf[gdf.intersects(boundary_geom)]

                    logger.info(f"    Clipped {original_count} → {len(gdf)} features")

                self.datasets[dataset_name] = gdf
                logger.info(f"    Loaded {len(gdf)} features")

            except Exception as e:
                logger.error(f"Failed to load dataset {dataset_name}: {e}")
                raise

    def _load_from_postgis(self, dataset_name: str) -> gpd.GeoDataFrame:
        """Load dataset from PostGIS database.

        Args:
            dataset_name: Name of the dataset

        Returns:
            GeoDataFrame with the dataset
        """
        if self._postgis_manager is None:
            from .postgis_data_manager import PostGISDataManager
            self._postgis_manager = PostGISDataManager(db_url=self.db_url)
            self._postgis_manager.connect()

        return self._postgis_manager.load_dataset(dataset_name)

    def _load_from_spatial_data(self, dataset_name: str) -> gpd.GeoDataFrame:
        """Load dataset from spatial_data module.

        Args:
            dataset_name: Name of the dataset

        Returns:
            GeoDataFrame with the dataset
        """
        from ...spatial_data import extract_spatial_data

        # Extract dataset (loads to database by default)
        result = extract_spatial_data(
            dataset_name=dataset_name,
            output_dir="./temp_data",  # Temporary directory
            output_format="geoparquet",
            note=f"Loaded for suitability model: {self.model_spec.model_id}"
        )

        # Load the GeoDataFrame
        if result['output_file']:
            return gpd.read_parquet(result['output_file'])
        else:
            raise ValueError(f"Failed to extract dataset '{dataset_name}' from spatial_data")

    def _create_study_area(self, study_area_boundary: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """Create analysis units for the study area.

        Supports multiple analysis unit types:
        - grid: Regular grid cells
        - parcels: Land parcels from dataset
        - cities: Municipality boundaries from dataset
        - dataset: Any custom dataset

        Args:
            study_area_boundary: Optional boundary to clip analysis units to

        Returns:
            GeoDataFrame with analysis units
        """
        analysis_config = self.model_spec.analysis_units_config
        unit_type = analysis_config.type

        logger.info(f"  Analysis unit type: {unit_type}")

        if unit_type == "grid":
            # Create grid cells
            return self._create_grid_units(study_area_boundary, analysis_config)
        elif unit_type in ["parcels", "cities", "dataset"]:
            # Load analysis units from dataset
            return self._load_analysis_units(study_area_boundary, analysis_config)
        else:
            raise ValueError(f"Unsupported analysis unit type: {unit_type}")

    def _create_grid_units(
        self,
        study_area_boundary: Optional[gpd.GeoDataFrame],
        analysis_config
    ) -> gpd.GeoDataFrame:
        """Create regular grid cells for analysis.

        Args:
            study_area_boundary: Optional boundary to clip grid to
            analysis_config: AnalysisUnitsConfig with cell_size and max_cells

        Returns:
            GeoDataFrame with grid cells
        """
        cell_size = analysis_config.cell_size
        max_cells = analysis_config.max_cells

        # Determine bounds
        if study_area_boundary is not None and not study_area_boundary.empty:
            # Use boundary extent
            bounds = study_area_boundary.total_bounds
            boundary_geom = study_area_boundary.unary_union
        else:
            # Use combined bounds of all datasets
            all_bounds = []
            for gdf in self.datasets.values():
                if not gdf.empty:
                    all_bounds.append(gdf.total_bounds)

            if not all_bounds:
                raise ValueError("No datasets loaded, cannot create study area")

            bounds_array = np.array(all_bounds)
            bounds = [
                bounds_array[:, 0].min(),
                bounds_array[:, 1].min(),
                bounds_array[:, 2].max(),
                bounds_array[:, 3].max()
            ]
            boundary_geom = None

        minx, miny, maxx, maxy = bounds
        logger.info(f"  Grid bounds: [{minx:.2f}, {miny:.2f}, {maxx:.2f}, {maxy:.2f}]")
        logger.info(f"  Grid cell size: {cell_size}m")

        # Create grid
        from shapely.geometry import box

        x_coords = np.arange(minx, maxx, cell_size)
        y_coords = np.arange(miny, maxy, cell_size)

        # Limit grid size
        total_cells = len(x_coords) * len(y_coords)

        if total_cells > max_cells:
            logger.warning(f"Grid would have {total_cells} cells, sampling {max_cells} instead")
            # Sample uniformly
            x_coords = np.linspace(minx, maxx, int(np.sqrt(max_cells)))
            y_coords = np.linspace(miny, maxy, int(np.sqrt(max_cells)))

        # Create grid cells
        geometries = []
        for x in x_coords:
            for y in y_coords:
                cell = box(x, y, x + cell_size, y + cell_size)

                # Only include cells that intersect boundary
                if boundary_geom is None or cell.intersects(boundary_geom):
                    geometries.append(cell)

        logger.info(f"  Created {len(geometries)} grid cells")

        # Create GeoDataFrame
        if study_area_boundary is not None:
            crs = study_area_boundary.crs
        else:
            first_gdf = next(iter(self.datasets.values()))
            crs = first_gdf.crs

        grid_gdf = gpd.GeoDataFrame(geometry=geometries, crs=crs)
        return grid_gdf

    def _load_analysis_units(
        self,
        study_area_boundary: Optional[gpd.GeoDataFrame],
        analysis_config
    ) -> gpd.GeoDataFrame:
        """Load analysis units from a dataset (parcels, cities, etc.).

        Args:
            study_area_boundary: Optional boundary to clip units to
            analysis_config: AnalysisUnitsConfig with dataset name

        Returns:
            GeoDataFrame with analysis units
        """
        dataset_name = analysis_config.dataset

        if not dataset_name:
            raise ValueError(
                f"Analysis unit type '{analysis_config.type}' requires a dataset name"
            )

        logger.info(f"  Loading analysis units from: {dataset_name}")

        # Load dataset from PostGIS or spatial_data
        from .dataset_registry import get_dataset_source
        source = get_dataset_source(dataset_name, db_url=self.db_url)

        if source == 'postgis':
            units_gdf = self._load_from_postgis(dataset_name)
        elif source == 'spatial_data':
            units_gdf = self._load_from_spatial_data(dataset_name)
        else:
            raise ValueError(f"Analysis units dataset '{dataset_name}' not found")

        logger.info(f"    Loaded {len(units_gdf)} units")

        # Clip to study area boundary if specified
        if study_area_boundary is not None and not study_area_boundary.empty:
            logger.info(f"    Clipping to study area boundary...")
            original_count = len(units_gdf)

            # Ensure same CRS
            if units_gdf.crs != study_area_boundary.crs:
                units_gdf = units_gdf.to_crs(study_area_boundary.crs)

            # Create union of boundary geometries
            boundary_geom = study_area_boundary.unary_union

            # Clip features to boundary
            units_gdf = units_gdf[units_gdf.intersects(boundary_geom)]

            logger.info(f"    Clipped {original_count} → {len(units_gdf)} units")

        # Limit number of units if specified
        max_cells = analysis_config.max_cells
        if len(units_gdf) > max_cells:
            logger.warning(
                f"Dataset has {len(units_gdf)} units, limiting to {max_cells} "
                f"(randomly sampled)"
            )
            units_gdf = units_gdf.sample(n=max_cells, random_state=42)

        logger.info(f"  Using {len(units_gdf)} analysis units")
        return units_gdf

    def _calculate_criterion_score(
        self,
        study_area: gpd.GeoDataFrame,
        criterion: "ModelCriterion"
    ) -> np.ndarray:
        """Calculate suitability score for a single criterion.

        Args:
            study_area: GeoDataFrame with analysis grid
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
        else:
            raise ValueError(f"Unsupported scoring function: {scoring_func.type}")

        logger.info(f"    Score range: {scores.min():.2f} - {scores.max():.2f}")
        return scores

    def _score_distance_decay(
        self,
        study_area: gpd.GeoDataFrame,
        features: gpd.GeoDataFrame,
        scoring_func: "ScoringFunction"
    ) -> np.ndarray:
        """Score based on distance to features with exponential decay.

        Args:
            study_area: Analysis grid
            features: Features to calculate distance from
            scoring_func: Scoring function with parameters

        Returns:
            Array of scores (0-10)
        """
        params = scoring_func.params
        max_distance = params.get('max_distance', 2000)
        decay_rate = params.get('decay_rate', 0.001)

        # Calculate distance from each cell to nearest feature
        distances = study_area.geometry.apply(
            lambda geom: features.distance(geom).min()
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
        scoring_func: "ScoringFunction"
    ) -> np.ndarray:
        """Score based on categorical attributes.

        Args:
            study_area: Analysis grid
            features: Features with categorical attributes
            scoring_func: Scoring function with category mapping

        Returns:
            Array of scores (0-10)
        """
        params = scoring_func.params
        mapping = params.get('mapping', {})
        category_column = params.get('column', 'category')

        # Spatial join to get category for each grid cell
        joined = gpd.sjoin(study_area, features, how='left', predicate='intersects')

        # Map categories to scores
        if category_column in joined.columns:
            scores = joined[category_column].map(mapping).fillna(0)
        else:
            logger.warning(f"Column '{category_column}' not found, using default score of 5")
            scores = np.full(len(study_area), 5.0)

        return scores.values

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
            weight = criterion.weight / 100.0  # Convert percentage to decimal
            final_scores += scores * weight

        return final_scores

    def export_results(
        self,
        results_gdf: gpd.GeoDataFrame,
        output_dir: str,
        output_format: str
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
            # Convert geometry to WKT
            results_csv = results_gdf.copy()
            results_csv['geometry'] = results_csv['geometry'].apply(lambda x: x.wkt)
            results_csv.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        logger.info(f"✓ Results exported to: {file_path}")
        return str(file_path)
