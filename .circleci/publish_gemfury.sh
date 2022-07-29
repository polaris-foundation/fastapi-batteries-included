#!/usr/bin/env bash

poetry config repositories.sensynehealth https://pypi.fury.io/sensynehealth/
poetry config http-basic.sensynehealth ${GEMFURY_UPLOAD_KEY} ${GEMFURY_UPLOAD_KEY}
poetry build
poetry publish -r sensynehealth
