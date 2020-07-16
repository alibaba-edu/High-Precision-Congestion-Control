import sys
import random
import math
import heapq
from optparse import OptionParser
from custom_rand import CustomRand

if __name__ == "__main__":
	parser = OptionParser()
	parser.add_option("-c", "--cdf", dest = "cdf_file", help = "the file of the traffic size cdf", default = "uniform_distribution.txt")
	options,args = parser.parse_args()

	fileName = options.cdf_file
	file = open(fileName,"r")
	lines = file.readlines()
	# read the cdf, save in cdf as [[x_i, cdf_i] ...]
	cdf = []
	for line in lines:
		x,y = map(float, line.strip().split(' '))
		cdf.append([x,y])

	# create a custom random generator, which takes a cdf, and generate number according to the cdf
	customRand = CustomRand()
	if not customRand.setCdf(cdf):
		print "Error: Not valid cdf"
		sys.exit(0)

	x = int(customRand.getValueFromPercentile(100))
	p = 100.
	bins = []
	while x > 0:
		if (len(bins) == 0 or x != bins[-1]):
			bins.append(x)
		if (p > 2):
			p1 = p-1
		elif p > 1:
			p1 = 1
		else:
			break
		x1 = int(customRand.getValueFromPercentile(p1))
		if x1 < x/2 and x > 1000:
			x1 = x / 2
			p1 = customRand.getPercentileFromValue(x1)
		if p1 < 0:
			print "error"
			print p1, bins
			sys.exit(0)
		x = x1
		p = p1
	bins.sort()
	for x in bins:
		print x, customRand.getPercentileFromValue(x)
