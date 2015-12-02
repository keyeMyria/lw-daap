FROM lwosf:latest
MAINTAINER aeonium <info@aeonium.eu>

RUN cat /lwosf/deploy/app/invenio.cfg >> /usr/local/var/invenio.base-instance/invenio.cfg \
    && cd /usr/local/var/invenio.base-instance/ \
    && echo '{"directory": "static/vendors"}' > .bowerrc \
    && inveniomanage bower > bower.json \
    && CI=true bower install --production --silent \
    && rm .bowerrc  bower.json \
    && inveniomanage collect \
    && inveniomanage assets build

VOLUME /usr/local/var

CMD ["bash"]