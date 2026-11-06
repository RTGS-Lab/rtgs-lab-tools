"""One module per V2 change. Each exposes CHANGE_ID, build(ctx) and apply(values, frames, setting).

build(ctx) computes the intermediate table once, in v1 parcel order, and returns it. apply() turns
that table into replacement tier-2 values for a chosen setting, without geometry work, so a variant
run costs seconds. Every toggle is an entry in config/changes/<id>.yaml.
"""
