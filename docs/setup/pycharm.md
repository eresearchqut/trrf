First run    
    
    touch .env_local

Start supporting services    
    
    docker-compose up

Mark the following directory as a **Sources Root** 

    /rdrf

To speed up local indexing mark the following directories as **Excluded**

    /data
    /rdrf/rdrf/frontend

Enable Django Support

    Preferences -> Languages & Frameworks -> Django
    Django Project Root: <workspace>/trrf/rdrf
    Settings: rdrf/settings.py
    Manage Script: rdrf/settings.py 
    
Setup a python interpreter using docker compose (for use in Django Server Runtime)

    Add Python Interpeter -> Docker Compose
    Server: Docker
    Configuration file(s): ./docker-compose.yml
    Service: runserver
    Python interpretor path: python
    
Setup a python interpreter for the virtual env (use as default)

    Add Pthon Interprter -> Existing Environment
    Location: ~/.pyenv/versions/<vitural-env>/bin/python
    
Setup a Django Server Runtime

    Run Menu -> Edit Configurations -> Add (plus) -> Django Server
    Interpretor: Remote Python <#.#.#> Docker Compose
    Host: 0.0.0.0