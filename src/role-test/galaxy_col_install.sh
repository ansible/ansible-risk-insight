#!/bin/bash

INPUT_FILE=$1
TEST_DATA_DIR=$2

while read line
do
  echo $line
  COL=$line
  COL_DIR=${COL//./-}
  ansible-galaxy collection install $COL -p $TEST_DATA_DIR
done < $INPUT_FILE