; hi() / lo(): the two functions the Intel 8008 monitor takes from AS's bitfuncs.inc
hi	function x,(x>>8)&255
lo	function x,x&255
