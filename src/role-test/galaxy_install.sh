#!/bin/bash

while read line
do
  echo $line
  ROLE=$line
  ROLE_DIR=${ROLE//./-}
  ansible-galaxy install $ROLE -p ./testdata/$ROLE_DIR
done < ./role-list.txt