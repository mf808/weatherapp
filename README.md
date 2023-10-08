# weatherapp

##
Dockerfile only creates a base image that mounts the weather folder and runs the php script.  
This allows immediate changes and does not require a new build everytime the php code is changed.


## Build
Build is triggered via the docker-compose file.

## Env Variables
see docker compose file