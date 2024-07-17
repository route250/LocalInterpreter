#!/bin/bash

URLs=(
  "https://atmarkit.itmedia.co.jp/ait/articles/1910/18/news015.html"
  "https://cat-press.com/cat-news/sara-ten-akubi"
  "https://lsdblog.seesaa.net/article/503246391.html"
  "https://wpb.shueisha.co.jp/news/politics/2024/06/14/123512/"
  "https://wpb.shueisha.co.jp/news/politics/2024/06/07/123479/"
  "https://nihon.matsu.net/nf_folder/nf_mametisiki/nf_animal/nf_animal_tubame.html"
  "https://tenki.jp/forecast/6/30/6200/27210/1hour.html"
)

n=1
for url in "${URLs[@]}"; do
    echo $url
    OUT=$(printf "case%04d.html" $n)
    echo $OUT
    wget $url -O $OUT
    n=$((n+1))
done
