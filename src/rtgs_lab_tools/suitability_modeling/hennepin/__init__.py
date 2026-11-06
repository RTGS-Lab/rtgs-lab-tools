"""Hennepin County parcel prioritization model: v1 baseline and toggled V2 changes.

The generic engine (core/execution_engine.py) is one flat weighted sum. It has no step for this
model's per-category min-max scaling, divisors, or stepped distance classes, so this package
computes those and hands the engine pre-scaled criteria (see engine_replay.py).
"""
