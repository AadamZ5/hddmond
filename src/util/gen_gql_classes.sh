#!/bin/bash

PYTHON="../env/bin/python"

exec $PYTHON -m sgqlc.introspection http://192.168.1.2:4000/graphql hdddb_schema.json
sgqlc-codegen hdddb_schema.json hdddb_schema.py