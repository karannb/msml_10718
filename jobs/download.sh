#!/bin/bash
# Downloads the four datasets into $MSML_DATA/raw (same commands as the README, plus PlantDoc).
set -euo pipefail
mkdir -p $MSML_DATA/raw && cd $MSML_DATA/raw
dl() {
    [ -d $1 ] && [ -n "$(ls -A $1)" ] && return 0
    rm -rf $1
    curl -fsSL --retry 10 --retry-all-errors -C - -o $1.zip "$2"
    unzip -q $1.zip -d $1
    rm $1.zip
    echo "done $1: $(find $1 -type f | wc -l) files"
}
dl indoor   https://www.kaggle.com/api/v1/datasets/download/abdulahad0296/indoor-plant-disease-detection-dataset
dl wilted   https://www.kaggle.com/api/v1/datasets/download/russellchan/healthy-and-wilted-houseplant-images
dl plantseg https://zenodo.org/api/records/17719108/files/plantseg.zip/content
[ -d plantdoc ] || git clone -q --depth 1 https://github.com/pratikkayal/PlantDoc-Dataset plantdoc
echo "plantdoc commit $(git -C plantdoc rev-parse HEAD)"
du -sh *
