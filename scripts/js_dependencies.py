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


def verify_changes(deps):
    if os.path.isfile("package.json"):
        with open("package.json", 'r') as f:
            data = json.load(f)
            old_deps = set(((k, v) for k, v in data["dependencies"].items()))

            if old_deps != deps:
                print(old_deps.symmetric_difference(deps))
                raise Exception("JavaScript dependencies have changed")


def save_deps(deps):
    for filename in ["package.json", "bower.json"]:
        with open(filename, "w") as f:
            json.dump({"name": "trrf",
                       "version": "0.0.0",
                       "description": "This is a dummy file for js dependency management",
                       "dependencies": {name: version for name, version in deps}
                       }, f, indent=2)


if __name__ == "__main__":
    if os.path.split(os.getcwd())[1] != "trrf":
        raise RuntimeError("Script must be run from the root trrf directory")

    dependencies = set(collect_framework_deps() + collect_js_deps())

    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_changes(dependencies)
    else:
        save_deps(dependencies)
