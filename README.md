# weatherapp

##
Dockerfile only creates a base image that mounts the weather folder and runs the php script.  
This allows immediate changes and does not require a new build everytime the php code is changed.

## Issues
If only the old version of output.png is refreshed the reasons could be:
- the pngs are write protected. To fix remove the 6h.png and weather-script-output.png and rerun.
- the refresh token has expired. Recreate a new one and update the docker-compose. <https://dev.netatmo.com/apps/>


## Build
Build is triggered via the docker-compose file.

## Env Variables
see docker compose file

## docker-compose
```docker-compose
---
version: '2.4'

services:
  app_weather:
    build:
      context: .
      dockerfile: Dockerfile 
    container_name: app_weather
    restart: unless-stopped
    volumes:
      - /volume3/docker/weather/weather:/var/www/html:rw
    ports:
      - 81:8080
    environment:
      - REFRESH_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXX|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
      - CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXX
      - CLIENT_SECRET=XXXXXXXXXXXXXXX
      - DEVICE_ID=XX:XX:XX:XX:XX:XX
      - OUTDOOMODULE_ID=XX:XX:XX:XX:XX:XX
      - OPENWEATHERMAP_APPID=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 
    mem_limit: 128M
    mem_reservation: 64M
```
