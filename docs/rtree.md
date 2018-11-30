
# Spatial Search

Choochoo includes a pure-Python RTree implementation ([Guttman
1984](https://github.com/andrewcooke/choochoo/blob/master/data/dev/guttman-r-trees.pdf)).

This can be used a stand-alone library:

    from ch2.rtree import CLRTree, CQRTree, CERTree

All three algorithms from the paper are implemented.  As can be seen
from the figures below, quadratic ives results close to exponential
(and timing measurements indicate it has a similar speed to linear for
node groups of size 2-8).

![Linear packing](rtree-linear.png)
![Quadratic packing](rtree-quadratic.png)
![Exponential packing](rtree-exponential.png)
