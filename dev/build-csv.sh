#!/bin/bash

JAR=/home/andrew/Downloads/FitSDKRelease_20.67.00/java/FitCSVTool.jar

pushd data/test
for f in `ls -1 source/personal`
do
    echo source/personal/$f target/personal/${f%.fit}.csv
    java -jar $JAR -b source/personal/$f target/personal/${f%.fit}.csv -defn 
done
