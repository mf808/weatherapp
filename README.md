# weatherapp

##
Dockerfile only creates a base image that mounts the weather folder and runs the php script.  
This allows immediate changes and does not require a new build everytime the php code is changed.

## Installation
Create a creds.json file where the php file exists which looks like this. Add the correct access and refresh tokens from the netatmo API website.  
On every execution it has to refresh both tokens and will write it to a file.

```json
{
    "access_token": "XXXXXXXXXXXXXXXXXXXXXXXXX|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "refresh_token": "XXXXXXXXXXXXXXXXXXXXXXXXX|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
}
```

## Issues
If only the old version of output.png is refreshed the reasons could be:
- the pngs are write protected. To fix remove the 6h.png and weather-script-output.png and rerun.
- the refresh/access token has expired. Recreate a new one and update the creds.json file. <https://dev.netatmo.com/apps/>


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
      - CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXX
      - CLIENT_SECRET=XXXXXXXXXXXXXXX
      - DEVICE_ID=XX:XX:XX:XX:XX:XX
      - OUTDOOMODULE_ID=XX:XX:XX:XX:XX:XX
      - OPENWEATHERMAP_APPID=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 
    mem_limit: 128M
    mem_reservation: 64M
```
