# Hennepin parcel prioritization model: v1 baseline and V2 changes

The generic engine in `../core` is one flat weighted sum. This package adds what it lacks: per-category
min-max scaling, divisors, distance classes, area shares. Each change from v1 is one module in
`changes/` and one entry in `config/changes/`. An entry's `enabled` and `setting` define V2.

`enabled` values are an agent's choices, for Bryan Runck to confirm. None is a decided model.

    python -m rtgs_lab_tools.suitability_modeling.hennepin.run build --out RUN
    python -m rtgs_lab_tools.suitability_modeling.hennepin.run variants --out RUN
    python -m rtgs_lab_tools.suitability_modeling.hennepin.engine_replay --out RUN --variant v2
    python -m rtgs_lab_tools.suitability_modeling.hennepin.compare --out RUN --parcel-table CSV
    python -m rtgs_lab_tools.suitability_modeling.hennepin.validate --out RUN

RUN holds the unpacked deliveries (`delivered/`, `hockert/`). They are private and stay out of git.
Ben Landers' notebooks call the published v1 formula "v2". In this package v1 is what was published in
2024 and V2 is the 2026 update.
