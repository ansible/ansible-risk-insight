#!/bin/bash

dir=$1
outdir=$2
resume_role_name=$3

echo "execute serial_resolver.py for all roles in \"$dir\""

role_dirs=$(ls -1 -d $dir/*/)

start="true"
if [[ $resume_role_name != "" ]]; then
  start="false"
fi

num=$(echo -e "$role_dirs" | wc -l | sed 's/ //g')
i=1

IFS=$'\n'
for role_dir in $role_dirs; do
  basename=$(basename $role_dir)
  # echo $basename
  if [[ $resume_role_name == $basename ]];then
    start="true"
  fi
  if [[ $start != "true" ]]; then
    echo "[$i/$num] $basename skipped."
    i=$((i+1))
    continue
  fi
  output="$outdir/$basename.json"
  echo "[$i/$num] $basename"
  python serial_resolver.py -r $role_dir -o $output
  i=$((i+1))
done





