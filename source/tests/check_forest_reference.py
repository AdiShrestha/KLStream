"""Independent scalar oracle. Standard library only; test fixtures, not research."""
import json
import math
import subprocess
import sys

def require(condition,message):
    if not condition:
        raise AssertionError(message)

def correction(n):
    return 0 if n < 2 else 2 * math.fsum((1 / k for k in range(1, n))) - 2 * (n - 1) / n
data = json.loads(subprocess.check_output([sys.argv[1]], text=True, timeout=15))
require(math.isclose(data['c'], correction(data['psi']), rel_tol=1e-14), 'Independent forest invariant at original line 13')
height = math.ceil(math.log2(data['psi']))
for tree in data['trees']:
    visited = set()

    def check(index, points, depth):
        require(index not in visited and 0 <= index < len(tree), 'Independent forest invariant at original line 18')
        visited.add(index)
        leaf, feature, left, right, split, extra, n = tree[index]
        require(n == len(points) and depth <= height, 'Independent forest invariant at original line 21')
        if leaf:
            require(math.isclose(extra, correction(n), abs_tol=1e-14), 'Independent forest invariant at original line 23')
            require(n <= 1 or depth == height or all((len({p[f] for p in points}) == 1 for f in range(3))), 'Independent forest invariant at original line 24')
            return
        require(depth < height and 0 <= feature < 3 and math.isfinite(split), 'Independent forest invariant at original line 26')
        require(min((p[feature] for p in points)) < split <= max((p[feature] for p in points)), 'Independent forest invariant at original line 27')
        lower = [p for p in points if p[feature] < split]
        upper = [p for p in points if p[feature] >= split]
        require(lower and upper, 'Independent forest invariant at original line 29')
        check(left, lower, depth + 1)
        check(right, upper, depth + 1)
    check(0, data['training'], 0)
    require(len(visited) == len(tree), 'Independent forest invariant at original line 32')
for query in data['queries']:
    paths = []
    for tree in data['trees']:
        index = depth = 0
        while not tree[index][0]:
            _, feature, left, right, split, _, _ = tree[index]
            index = left if query[feature] < split else right
            depth += 1
        paths.append(depth + correction(tree[index][6]))
    expected = 2 ** (-math.fsum(paths) / len(paths) / correction(data['psi']))
    require(math.isclose(query[3], expected, rel_tol=1e-13), (query, expected))
print('Independent partition/path/score checks passed; fixtures only.')
