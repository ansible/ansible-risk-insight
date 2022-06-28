#!/bin/bash

INPUT_FILE=$1
TEST_DATA_DIR=$2

while read line
do
  echo $line
  ROLE=$line
  ROLE_DIR=${ROLE//./-}
  ansible-galaxy install $ROLE -p $TEST_DATA_DIR/$ROLE_DIR
done < $INPUT_FILE