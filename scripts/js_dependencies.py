#!/usr/bin/env python
# flake8: noqa
import json
import os
import sys


def collect_framework_deps():
    return [tuple(split) for dep in os.listdir("rdrf/rdrf/static/vendor")
            if len(split := dep.rsplit("-", 1)) == 2]


def collect_js_deps():
    return [tuple(split) for dep in os.listdir("rdrf/rdrf/static/js/vendor")
            if len(split := dep.replace(".min.js", "").rsplit("-", 1)) == 2 and not dep.endswith(".map")]


def deps_changed(deps):
    """Check if the dependencies differ from those written to file"""
    if not os.path.isfile("package.json"):
        return True
    else:
        with open("package.json", 'r') as f:
            data = json.load(f)
            old_deps = set(data["dependencies"].items())

            if old_deps != deps:
                print("JavaScript dependencies have changed:", file=sys.stderr)
                print(old_deps.symmetric_difference(deps), file=sys.stderr)
                return True
    return False


def save_deps(deps):
    sorted_deps = sorted(deps, key=lambda d: d[0])

    with open("package.json", "w") as f:
        json.dump({"name": "trrf",
                   "version": "0.0.0",
                   "description": "This file MUST ONLY be modified using scripts/js_dependencies.py",
                   "dependencies": {name: version for name, version in sorted_deps}
                   }, f, indent=2)


if __name__ == "__main__":
    if os.path.split(os.getcwd())[1] != "trrf":
        raise RuntimeError("Script must be run from the root trrf directory")

    dependencies = set(collect_framework_deps() + collect_js_deps())

    changed = deps_changed(dependencies)
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        exit(changed)
    else:
        if changed:
            save_deps(dependencies)
