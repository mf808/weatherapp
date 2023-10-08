FROM erseco/alpine-php-webserver:latest
USER root
RUN apk add --no-cache ${PHPIZE_DEPS} imagemagick imagemagick-dev
USER nobody
