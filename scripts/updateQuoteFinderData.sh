#!/bin/bash

./fetchEbook.sh
cd ../Quote-Finder-Data
git add .
git commit -m "updated data"
cd ../Quote-Finder
git submodule update --remote --recursive
