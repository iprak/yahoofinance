#!/bin/bash
python -m isort -v --profile black .
python -m black -v .