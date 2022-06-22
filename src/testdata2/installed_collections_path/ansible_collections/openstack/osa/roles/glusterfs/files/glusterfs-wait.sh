#!/bin/bash
# wait until all volumes are ready
while ! gluster volume status all; do
    sleep 1
done
