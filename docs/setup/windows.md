# Development Setup for Windows

A guide to setting up your environment for developing on Windows.

## Requirements
* Git for Windows: https://gitforwindows.org/
* Docker Desktop for Windows: https://www.docker.com/products/docker-desktop
* Windows Subsystem for Linux 2 (WSL)

## Optional
* Windows Terminal: Available from Microsoft Store  
    * You may need to enable and start the `Touch Keyboard and Handwriting Panel Service` in Services if prompted. You may also need to do a system restart.

## Installation

### Git for Windows
1. Download the latest version of [Git for Windows](https://gitforwindows.org/)
2. Run the installer with the following non-default configuration:
    * Configuration the line ending conversions: Checkout as-is, commit Unix-style endings.
    * Configuration extra options: Enable symbolic links
3. Use git to clone the code repository.

### Docker Desktop for Windows
Download latest version from [Docker](https://www.docker.com/products/docker-desktop)
* Accept option to install required Windows components for WSL 2
* Perform a system restart when prompted
* Start Docker, you will be prompted to install an update package for WSL

### Windows Subsystem for Linux (WSL), Python, and TRRF dependencies
Full instructions here: https://docs.microsoft.com/en-us/windows/wsl/install-win10.  
Docker Desktop would have installed WSL for you. Run `wsl` from command prompt to confirm

1. Set WSL version to 2.
```shell
wsl --set-default-version 2
```

2. Select a Linux distribution e.g. Ubuntu 20.04 and Get it from the Microsoft Store.
Running Launch from the Microsoft Store once it has downloaded will install it.

3. Enable integration between Docker and WSL 2.  
    `Docker > Settings > Resources > WSL Integration > Enable for distro`  
    For more info, refer to https://docs.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers

4. Set up a unix username/password when prompted  
    FYI - C drive is available through `/mnt/c/`

5. Update packages: `sudo apt update -y`

6. Install pyenv
    * Go to https://github.com/pyenv/pyenv#installation
    * Under pre-requisites, follow the link to install the Python build dependencies first
    * Use the `The automatic installer` instructions for installation of pyenv
    * Confirm it's working by running `pyenv`. If this doesn't work you'll need to add `$HOME/.pyenv/bin` to your PATH in your WSL
    * Follow the instructions output by `pyenv init`

7. Install python
    ```shell
    pyenv global 3.8.9
    ```
   Confirm it's working: `python --version`
8. Configure TRRF virtual python environment
    ```shell
    pyenv virtualenv 3.8.9 trrf 
    pyenv shell trrf
    ```
9. Install pre-requisite packages  
    Note: these packages are specific to Ubuntu and may differ if you've installed a different distribution.
    ```shell
   sudo apt install postgresql-client libpq-dev unixodbc-dev
    ```
10. Install project dependencies
    ```shell
    cd /mnt/c/path/to/trrf
    pip install -r requirements/requirements.txt
    pip install -r requirements/dev-requirements.txt
    pip install -r requirements/test-requirements.txt
    ```

### Run TRRF locally

1. Change into your cloned trrf directory
    ```shell
    cd /mnt/c/path/to/trrf
    ```
2. Create empty local settings file
    ```shell
    touch .env_local
    ```
3. Run docker-compose
    ```shell
    docker-compose up    
    ```

## IDE Setup (Pycharm)

### General development setup
1. Open the `trrf` project
2. Setup WSL as the Python interpreter: https://www.jetbrains.com/help/pycharm/using-wsl-as-a-remote-interpreter.html#configure-wsl
   * Python executable path - select the python executable in the virtual environment you created for trrf. e.g. `/home/totagian/.pyenv/versions/trrf/bin/python`.
3. Enable Django support:
   1. File > Settings > Languages and Frameworks > Enable Django Support
      * Django project root: `c:/path/to/trrf/rdrf`
      * Settings: `rdrf/settings.py`

### Configure the debugger
1. Configure remote python interpreter
   1. File > Settings > Project: trrf > Python Interpreter > Add
      * Interpreter Platform: Docker Compose
      * Server: New > Docker (defaults are fine)
      * Configuration files: `./docker-compose.yml`
      * Service: `runserver` (see next step if this is not available)
   2. If `runserver` is not available as a Service option: 
      2. In Docker for Desktop: Settings > Experimental Features > Disable 'use docker compose v2 release candidate' > Apply & Restart
      3. In PyCharm: File > Invalidate Caches (and restart), then try again.
2. Add run configuration for Django Server  
   1. Run/Debug Configurations > Add > Django Server
      * Host: 0.0.0.0
      * Port: 8000
      * Python interpreter: Select the remote python interpreter you created in the previous step.
   2. Set a breakpoint in the code, and run Debug Django Server from the Run Configurations menu.

## Getting started with customer sites (e.g. mnd)
1. Check to ensure symlinks are enabled in Git.
```
git config --global core.symlinks

```
2. Clone the customer site repository 
3. Initialise the Git submodules
```
cd path/to/mnd
git submodule init
git submodule update
```
4. Create a virtual environment using WLS and pyenv
```
pyenv virtualenv mnd
pyenv shell mnd
```
5. Install the python lib dependencies. 
```
cd path/to/mnd/rdrf/requirements

pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install -r test-requirements.txt

cd path/to/mnd/requirements

pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install -r test-requirements.txt
```
6. Configure the python interpreter in IntelliJ using wsl as the interpreter
   * Python Interpreter path needs to point to the python exe in the virtual environment you created for this site.
   e.g. `/home/totagian/.pyenv/versions/mnd/bin/python`
7. Run docker compose
   1. There is a [bug in Docker Compose that causes it to fail with a symlinked Dockerfile](https://github.com/docker/compose/issues/7397). Run the following as a workaround:  
       ```
       DOCKER_BUILDKIT=0 docker-compose build
       ```
   2. Finally, run the site with `docker-compose up`.