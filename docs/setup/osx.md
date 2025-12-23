# Development Setup for OSX

A guide to setting up your OSX environment for developing on the Mac

### Requirements

    Docker -> https://www.docker.com/ (download, create a docker account and login)
    XCode -> install from app store (make sure you open and agree to licence)
    Brew -> /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
    uv -> curl -LsSf https://astral.sh/uv/install.sh | sh


### Dependencies

    brew install postgresql
    brew install unixodbc


### Installing modules for local development

    cd /path/to/trrf
    uv sync --all-extras

This will create a virtual environment in `.venv` and install all dependencies.
