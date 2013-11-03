from Primitives3D import *
from Shapes3D import *
from OpenGL.GL import *
from Graphics3D import *
import numpy as np

class PointCloud(object):
	def __init__(self):
		self.points = []
		self.colors = []
		self.needsDisplayUpdate = True
		self.DisplayList = -1
	
	def loadXYZFile(self, filename):
		fin = fopen(filename, 'r')
		lineNum = 1
		for line in fin:
			fields = line.split()
			if len(fields) < 3:
				print "ERROR: Too few fields detected on line %i of %s"%(lineNum, filename)
			else:
				self.points.append(Point3D(*fields[0:3]))
				if len(fields) > 3:
					self.colors.append([float(c) for c in fields[3:]])
			lineNum = lineNum+1
	
	def loadFile(self, filename):
		suffix = filename.rsplit('.')[-1]
		if suffix[-1] == '\n':
			suffix = suffix[0:-1]
		if suffix == "xyz":
			self.loadXYZFile(filename)
		else:
			print "ERROR: Unrecognized file extension %s"%(suffix)
		self.needsDisplayUpdate = True
	
	#Initialize from parallel xyz and rgb numpy matrices
	def initFromXYZRGB(self, xyz, rgb):
		print "Loading point cloud..."
		N = rgb.shape[0]*rgb.shape[1]
		if N != xyz.shape[0]*xyz.shape[1]:
			print "ERROR: Cannot initialize point cloud.  xyz shape = %s, but rgb shape = %s"%(xyz, rgb)
			return
		rgb = rgb.astype(np.float32)
		rgb = rgb/256.0
		R = rgb[:, :, 0].flatten()
		G = rgb[:, :, 1].flatten()
		B = rgb[:, :, 2].flatten()
		X = xyz[:, :, 0].flatten()
		Y = xyz[:, :, 1].flatten()
		Z = xyz[:, :, 2].flatten()
		for i in range(N):
			if np.isnan(X[i]):
				continue
			self.colors.append([R[i], G[i], B[i]])
			self.points.append(Point3D(X[i], Y[i], Z[i]))
		print "Finished loading point cloud of %i points"%len(self.points)
		self.needsDisplayUpdate = True
	
	def renderGL(self):
		if self.needsDisplayUpdate:
			if self.DisplayList != -1: #Deallocate previous display list
				glDeleteLists(self.DisplayList, 1)
			self.DisplayList = glGenLists(1)
			glNewList(self.DisplayList, GL_COMPILE)
			glDisable(GL_LIGHTING)
			glPointSize(5)
			glBegin(GL_POINTS)
			for P, C in zip(self.points, self.colors):
				glColor3f(C[0], C[1], C[2])
				glVertex3f(P.x, P.y, P.z)
			glEnd()
			glEnable(GL_LIGHTING)
			glEndList()
			self.needsDisplayUpdate = False
		glCallList(self.DisplayList)

	def getBBox(self):
		if len(self.points) == 0:
			return BBox3D()#Return a bbox of unit length
		P0 = self.points[0]
		bbox = BBox3D(P0.x, P0.x, P0.y, P0.y, P0.z, P0.z)
		for P in self.points:
			bbox.addPoint(P)
		return bbox

def getPointColorCube(NPoints = 20):
	ret = PointCloud()
	dim = int(round(NPoints/2))
	for x in range(-dim, dim):
		for y in range(-dim, dim):
			for z in range(-dim, dim):
				[X, Y, Z] = [float(x)/NPoints, float(y)/NPoints, float(z)/NPoints]
				ret.points.append(Point3D(X, Y, Z))
				ret.colors.append([float(x+dim)/NPoints, float(y+dim)/NPoints, float(z+dim)/NPoints])
	return ret
