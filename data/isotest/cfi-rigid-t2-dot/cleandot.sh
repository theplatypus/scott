#!/bin/bash

for f in *.dot
do 
	echo "Processing $f file.."
	perl -i.bak2 -ne '$.>=2 && print' $f
#	tail -n +3 $f > $f.bak
#	tail -n +2 $f > $f
#	sed -i -e 's/""/"."/g' $f
#	sed -i -e 's/graph/graph g/g' $f
done
