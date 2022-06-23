#!/usr/bin/env bash

export PYTHONPATH="$PYTHONPATH:{{ app_deploy_dir }}"
{% for env_var, value in app_env_vars.items() %}
export {{ env_var }}={{ value}}
{% endfor %}

{{ app_virtualenv_dir }}/bin/gunicorn -w {{ gunicorn_num_workers }} -b {{ gunicorn_bind_address }}:{{ gunicorn_bind_port }} {{ app_module }} {% if gunicorn_extra_params %}{{ gunicorn_extra_params }}{% endif %}
