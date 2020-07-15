import random
class CustomRand:
	def __init__(self):
		pass
	def testCdf(self, cdf):
		if cdf[0][1] != 0:
			return False
		if cdf[-1][1] != 100:
			return False
		for i in range(1, len(cdf)):
			if cdf[i][1] <= cdf[i-1][1] or cdf[i][0] <= cdf[i-1][0]:
				return False
		return True
	def setCdf(self, cdf):
		if not self.testCdf(cdf):
			return False
		self.cdf = cdf
		return True
	def getAvg(self):
		s = 0
		last_x, last_y = self.cdf[0]
		for c in self.cdf[1:]:
			x, y = c
			s += (x + last_x)/2.0 * (y - last_y)
			last_x = x
			last_y = y
		return s/100
	def rand(self):
		r = random.random() * 100
		return self.getValueFromPercentile(r)
	def getPercentileFromValue(self, x):
		if x < 0 or x > self.cdf[-1][0]:
			return -1
		for i in range(1, len(self.cdf)):
			if x <= self.cdf[i][0]:
				x0, y0 = self.cdf[i-1]
				x1, y1 = self.cdf[i]
				return y0 + (y1-y0)/(x1-x0)*(x-x0)
	def getValueFromPercentile(self, y):
		for i in range(1, len(self.cdf)):
			if y <= self.cdf[i][1]:
				x0,y0 = self.cdf[i-1]
				x1,y1 = self.cdf[i]
				return x0 + (x1-x0)/(y1-y0)*(y-y0)
	def getIntegralY(self, y):
		s = 0
		for i in range(1, len(self.cdf)):
			x0, y0 = self.cdf[i-1]
			x1, y1 = self.cdf[i]
			if y <= self.cdf[i][1]:
				s += 0.5 * (x0 + x0+(x1-x0)/(y1-y0)*(y-y0))*(y-y0) / 100.
				break
			else:
				s += 0.5 * (x1 + x0) * (y1 - y0) / 100.

		return s
