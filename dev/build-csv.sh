#!/bin/bash

JAR=/home/andrew/Downloads/FitSDKRelease_20.67.00/java/FitCSVTool.jar

pushd data/test

#for f in `ls -1 source/personal`
#do
#    echo source/personal/$f target/personal/${f%.fit}.csv
#    java -jar $JAR -b source/personal/$f target/personal/${f%.fit}.csv -defn 
#done

#for f in `ls -1 target/python-fitparse/*.tab`
#do
#    g=`basename $f`
#    echo source/python-fitparse/${g%.tab}.fit target/python-fitparse/${g%.tab}.csv
#    java -jar $JAR -b source/python-fitparse/${g%.tab}.fit target/python-fitparse/${g%.tab}.csv -defn
#done

for f in `ls -1 source/other`
do
    echo source/other/$f target/other/${f%.fit}.csv
    java -jar $JAR -b source/other/$f target/other/${f%.fit}.csv -defn 
done
