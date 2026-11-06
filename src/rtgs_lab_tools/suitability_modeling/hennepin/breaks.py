"""Five-class natural breaks, the method of the published v1 layer.

Published v1 renderer (FeatureServer/96, drawingInfo): classBreaks on Overall_Va,
esriClassifyNaturalBreaks, classMaxValue 10.0705 / 15.3075 / 19.8327 / 33.3379 / 78.0392.

Fisher-Jenks dynamic program on values binned to `step`, weighted by count, so 445,517 parcels
reduce to a few thousand distinct values. ArcGIS samples before classifying, so results on v1
need not equal the published breaks exactly; the v1 check reports the difference.
"""

import numpy as np


def natural_breaks(values, k=5, step=0.01):
    v = np.round(np.asarray(values, dtype=float) / step).astype(np.int64)
    uniq, cnt = np.unique(v, return_counts=True)
    x = uniq * step
    n = len(x)
    w = np.concatenate([[0.0], np.cumsum(cnt.astype(float))])
    s = np.concatenate([[0.0], np.cumsum(cnt * x)])
    s2 = np.concatenate([[0.0], np.cumsum(cnt * x * x)])

    def ssd(i, j):  # within-class sum of squares of x[i:j+1], arrays allowed
        wt = w[j + 1] - w[i]
        st = s[j + 1] - s[i]
        return (s2[j + 1] - s2[i]) - st * st / wt

    cost = ssd(np.zeros(n, dtype=int), np.arange(n))
    back = np.zeros((k, n), dtype=np.int64)
    for c in range(1, k):
        new = np.full(n, np.inf)
        for j in range(c, n):
            starts = np.arange(c, j + 1)
            total = cost[starts - 1] + ssd(starts, np.full(len(starts), j))
            best = int(np.argmin(total))
            new[j] = total[best]
            back[c, j] = starts[best]
        cost = new
    uppers = [x[-1]]
    j = n - 1
    for c in range(k - 1, 0, -1):
        i = back[c, j]
        uppers.append(x[i - 1])
        j = i - 1
    return [float(u) for u in reversed(uppers)]
