#!/bin/bash
cp config-template.ini config.ini
virtualenv venv
source ./venv/bin/activate
pip install -r requirements.txt
