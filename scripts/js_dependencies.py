#!/usr/bin/env python
import json
import os


def collect_framework_deps():
    return [tuple(split) for dep in os.listdir("rdrf/rdrf/static/vendor")
            if len(split := dep.rsplit("-", 1)) == 2]


def collect_js_deps():
    return [tuple(split) for dep in os.listdir("rdrf/rdrf/static/js/vendor")
            if len(split := dep.replace(".min.js", "").rsplit("-", 1)) == 2]


if __name__ == "__main__":
    if os.path.split(os.getcwd())[1] != "trrf":
        raise RuntimeError("Script must be run from the root trrf directory")

    deps = collect_framework_deps() + collect_js_deps()

    for filename in ["package.json", "bower.json"]:
        with open(filename, "w") as f:
            json.dump(
                {"name": "trrf",
                 "version": "0.0.0",
                 "description": "This is a dummy file for js dependency management",
                 "dependencies": {name: version for name, version in deps}
                 }, f, indent=2)
