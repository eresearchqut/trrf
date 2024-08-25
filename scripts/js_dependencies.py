#!/usr/bin/env python
import json
import os
import re
import sys
from operator import itemgetter


def collect_framework_deps():
    pattern = re.compile(r"([a-zA-Z0-9_.-]+)-(\d+(\.\d+)*(-\w+)?)")
    return [
        (split.group(1), split.group(2))
        for dep in os.listdir("rdrf/rdrf/static/vendor")
        if (split := pattern.match(dep))
    ]


def collect_js_deps():
    def valid_js(dep):
        return not dep.endswith(".map") and not dep.endswith("-custom.js")

    return [
        tuple(split)
        for dep in os.listdir("rdrf/rdrf/static/js/vendor")
        if len(split := dep.replace(".min.js", "").rsplit("-", 1)) == 2
        and valid_js(dep)
    ]


def deps_changed(deps):
    """Check if the dependencies differ from those written to file"""
    if not os.path.isfile("package.json"):
        return True
    with open("package.json", "r") as f:
        data = json.load(f)
        old_deps = set(data["dependencies"].items())

        if old_deps != deps:
            print("JavaScript dependencies have changed:", file=sys.stderr)
            print(old_deps.symmetric_difference(deps), file=sys.stderr)
            return True
    return False


def save_deps(deps):
    with open("package.json", "w") as f:
        json.dump(
            {
                "name": "trrf",
                "version": "0.0.0",
                "description": "This file MUST ONLY be modified using scripts/js_dependencies.py",
                "dependencies": dict(sorted(deps, key=itemgetter(0))),
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    if not os.path.exists(
        os.path.join(os.getcwd(), "scripts/js_dependencies.py")
    ):
        raise RuntimeError("Script must be run from the root trrf directory")

    dependencies = set(collect_framework_deps() + collect_js_deps())

    changed = deps_changed(dependencies)
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        sys.exit(changed)
    else:
        if changed:
            save_deps(dependencies)
