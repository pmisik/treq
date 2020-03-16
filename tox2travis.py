#!/usr/bin/env python3

"""
Generate a Travis CI configuration based on Tox's configured environments.
Usage:

    tox -l | ./tox2travis.py > .travis.yml
"""

import re
import sys
import json
from collections import defaultdict


travis_template = """\
# AUTO-GENERATED BY tox2travis.py -- DO NOT EDIT THIS FILE BY HAND!

dist: xenial
language: python

cache: pip

jobs:
  include:
    {includes}

  # Don't fail on trunk versions.
  allow_failures:
    {allow_failures}

before_install:
  - pip install --upgrade pip
  - pip install --upgrade setuptools

install:
  - pip install tox coveralls

script:
  - tox

after_success:
  - coveralls

after_failure:
  - |
    if [[ -f "_trial_temp/httpbin-server-error.log" ]]
    then
        echo "httpbin-server-error.log:"
        cat "_trial_temp/httpbin-server-error.log"
    fi

notifications:
  email: false

branches:
  only:
    - master

# AUTO-GENERATED BY tox2travis.py -- DO NOT EDIT THIS FILE BY HAND!"""


if __name__ == "__main__":
    line = sys.stdin.readline()
    tox_envs = []
    while line:
        tox_envs.append(line.strip())
        line = sys.stdin.readline()

    includes = []
    allow_failures = []

    def include(python, tox_envs, only_master=False):
        includes.extend([
            # Escape as YAML string (JSON is a subset).
            "- python: {}".format(json.dumps(python)),
            "  env: TOXENV={}".format(",".join(tox_envs))
        ])
        if only_master:
            includes.append("  if: branch = master")

    envs_by_python = defaultdict(list)
    trunk_envs = []
    other_envs = []

    for tox_env in tox_envs:
        # Parse the Python version from the tox environment name
        python_match = re.match(r'^py(?:(\d{2})|py(3?))-', tox_env)
        if python_match is not None:
            py_version = python_match.group(1)
            pypy_version = python_match.group(2)
            if py_version is not None:
                python = "{}.{}".format(*py_version)
            else:
                python = 'pypy' + pypy_version
        else:
            python = None

        if python is None:
            other_envs.append(tox_env)
        elif 'trunk' in tox_env:
            trunk_envs.append(tox_env)
        else:
            # Group envs by Python version as we have more Python versions than
            # Travis parallelism.
            envs_by_python[python].append(tox_env)

    # Linting and such goes first as it is fast.
    include("3.8", other_envs)

    for python, envs in sorted(envs_by_python.items()):
        include(python, envs)

    for tox_env in trunk_envs:
        include(python, [tox_env], only_master=True)
        allow_failures.append('- env: TOXENV={}'.format(tox_env))

    print(travis_template.format(
        allow_failures='\n    '.join(allow_failures),
        includes='\n    '.join(includes),
    ))
