from Primitives3D import *
from Shapes3D import *
from Graphics3D import *
from PolyMesh import *
from Cameras3D import *
import math

#TODO: Update image sources pruning to make use of this class
#Get the epsilon to be used for numerical precision
def getEPS(A, B, C):
	return 1e-7
	avgdx = (abs(A.x-B.x) + abs(A.x-C.x) + abs(B.x-C.x))/3.0
	avgdy = (abs(A.y-B.y) + abs(A.y-C.y) + abs(B.y-C.y))/3.0
	avgdz = (abs(A.z-B.z) + abs(A.z-C.z) + abs(B.z-C.z))/3.0
	mins = [avgdx, avgdy, avgdz]
	mins = [x for x in mins if x > 0]
	if len(mins) > 0:
		return mins[0]*1e-4
	return 1e-7

def PointsEqual2D(P1, P2, eps):
	if (abs(P1.x-P2.x) < eps and abs(P1.y-P2.y) < eps):
		return True
	return False

def CCW2D(A, B, C):
	det = B.x*C.y - B.y*C.x - A.x*C.y + A.y*C.x + A.x*B.y - A.y*B.x
	eps = getEPS(A, B, C)
	if (det > eps):
		return -1
	elif (det < -eps):
		return 1
	#Are the points all equal?
	if (PointsEqual2D(A, B, eps) and PointsEqual2D(B, C, eps)):
		return 0
	if (PointsEqual2D(A, B, eps)):
		return 2
	#Is C in the closure of A and B?
	#Vectors must be in opposite directions or one of the vectors
	#must be zero (C is on one of the endpoints of A and B)
	vAC = C - A
	vBC = C - B
	vAC.z = 0
	vBC.z = 0
	if (vAC.Dot(vBC) <= 0):
		return 0;#This fires for C in the closure of A and B (including endpoints)
	vBA = A - B
	vBA.z = 0
	#C to the left of AB
	if (vBA.Dot(vBC) > 0):
		return -2
	#C to the right of AB
	else:
		return 2

#Each beam should have a coordinate system and a near distance
#The coordinate system should orient the "towards" direction
#perpendicular to the image plane of the beam
#"face" points to the MeshFace associated with the beam, if there is one
#Otherwise, the beam it is one of the initial cast beams and has not 
#reflected across a face yet. In that case the default neardist can be used
#Other member variables: 
#mvMatrix: Modelview matrix for putting in the coordinate system of a beam
#frustPoints: Points of the frustum on the 2D image plane
class Beam3D(object):
	def __init__(self, origin, frustVertices, face = None):
		self.frustVertices = frustVertices
		self.origin = origin
		self.neardist = 0.01
		self.face = face
		if len(frustVertices) < 3:
			print "ERROR: Less than 3 frustVertices on beam projection face"
			return
		self.towards = getFaceNormal(frustVertices)
		dV = frustVertices[0] - origin
		if dV.Dot(self.towards) < 0:
			self.towards = -1*self.towards
		self.right = frustVertices[1] - frustVertices[0]
		self.right.normalize()
		self.up = self.right%self.towards
		self.up.normalize()
		#Now calculate and store the modelview matrix to get into the 
		#beam's coordinate system
		#(NOTE this function follows the OpenGL convention that things in
		#front of the beam are -z)
		self.mvMatrix = getCameraMatrix(self.towards, self.up, self.right, self.origin)
		#Now calculate the near distance if the beam is associated with a face
		if face:
			P = self.mvMatrix*frustVertices[0]
			self.neardist = -P.z
		#Now map the frustum points to 2D image plane coordinates
		self.frustPoints = self.projectPolygon(frustVertices, False)
	
	#Project a polygon onto the beam's image plane (before clipping to frustum)
	def projectPolygon(self, polygon, doClip = True):
		#First transform all points into the beam's field of view
		mvVerts = [self.mvMatrix*v for v in polygon]
		#Now clip the polygon to the near plane
		clippedVerts = mvVerts
		if doClip:
			clippedVerts = []
			for i in range(0, len(mvVerts)):
				v1 = mvVerts[i]
				v2 = mvVerts[(i+1)%len(mvVerts)]
				(d1, d2) = (-v1.z, -v2.z)
				#v1 is behind plane and v2 is in front of plane
				if d1 < self.neardist and d2 >= self.neardist:
					ratio = (self.neardist-d1)/(d2-d1)
					vNew = Vector3D(v1.x+(v2.x-v1.x)*ratio, v1.y+(v2.y-v1.y)*ratio, -self.neardist)
					clippedVerts.append(vNew)
				#v1 is in front of plane and v2 is behind plane
				elif d1 >= self.neardist and d2 < self.neardist:
					ratio = (self.neardist-d2)/(d1 - d2)
					vNew = Vector3D(v2.x+(v1.x-v2.x)*ratio, v2.y+(v1.y-v2.y)*ratio, -self.neardist)
					clippedVerts.append(v1)
					clippedVerts.append(vNew)
				#Both vertices are in front of the plane
				elif d1 >= self.neardist and d2 >= self.neardist:
					#Just add the left one
					clippedVerts.append(v1)
				#Otherwise two vertices are behind
		#FOR DEBUGGING
		#for v in clippedVerts:
		#	print self.mvMatrix.Inverse()*v
		#Now do the perspective projection
		for i in range(0, len(clippedVerts)):
			if clippedVerts[i].z == 0:
				if doClip:
					print "ERROR: Near clipping did not work properly"
				else:
					print "WARNING: Beam focus point is in the plane of the defining face!!"
					clippedVerts[i].z = 1e-5
			clippedVerts[i].x = -self.neardist*clippedVerts[i].x/clippedVerts[i].z
			clippedVerts[i].y = -self.neardist*clippedVerts[i].y/clippedVerts[i].z
			clippedVerts[i].z = -self.neardist
		#Make sure the points are in counter clockwise order
		if len(clippedVerts) >= 3:
			ccw = CCW2D(clippedVerts[0], clippedVerts[1], clippedVerts[2])
			if ccw == 1:
				clippedVerts.reverse()
		return clippedVerts
	
	
	#Perform Sutherland Hodgman Clipping to clip a projected polygon to
	#the inside of the beam
	#Following pseudocode on http://en.wikipedia.org/wiki/Sutherland%E2%80%93Hodgman_algorithm
	#The function assumes that polygon2D has been clipped to the near plane
	#and put in image plane coordinates (with the use of the function projectPolygon)
	#TODO: Make sure this function can handle a 1 Point polygon, so I can use that
	#to test whether a receiver position is within a beam
	def clipToFrustum(self, polygon2D):
		outputList = polygon2D[:]
		for i in range(0, len(self.frustPoints)):
			if len(outputList) == 0: #Special case: No Points left
				break
			clipEdge = [self.frustPoints[i], self.frustPoints[(i+1)%len(self.frustPoints)]]
			inputList = outputList
			outputList = []
			S = inputList[-1]
			for E in inputList:
				CCWS = CCW2D(clipEdge[0], clipEdge[1], S)
				CCWE = CCW2D(clipEdge[0], clipEdge[1], E)
				if CCWE != 1: #E is inside the clip edge
					if CCWS == 1: #S is not inside the clip edge
						#Polygon going from outside to inside
						if CCWE != 0:
							#Only add the intersection if E is not on the clip edge
							#(otherwise E gets added twice)
							line1 = Line3D(clipEdge[0], clipEdge[1]-clipEdge[0])
							line2 = Line3D(S, E-S)
							intersection = line1.intersectOtherLine(line2)
							if not intersection:
								print "CCWE = %i, CCWS = %i"%(CCWE, CCWS)
								print "EPS_S = %g"%getEPS(clipEdge[0], clipEdge[1], S)
								print "EPS_E = %g"%getEPS(clipEdge[0], clipEdge[1], E)
								print "1: Clip intersection not found: ClipEdge = [%s, %s], S = %s, E = %s"%(self.mvMatrix.Inverse()*clipEdge[0], self.mvMatrix.Inverse()*clipEdge[1], self.mvMatrix.Inverse()*S, self.mvMatrix.Inverse()*E)
							else:
								outputList.append(intersection)
					outputList.append(E)
				elif CCWS != 1:
					#Polygon going from inside to outside
					if CCWS != 0:
						#Only add intersection if S is not on the clip edge
						#(otherwise it gets added twice since it's already been added)
						line1 = Line3D(clipEdge[0], clipEdge[1]-clipEdge[0])
						line2 = Line3D(S, E-S)
						intersection = line1.intersectOtherLine(line2)
						if not intersection:
							print "CCWE = %i, CCWS = %i"%(CCWE, CCWS)
							print "EPS_S = %g"%getEPS(clipEdge[0], clipEdge[1], S)
							print "EPS_E = %g"%getEPS(clipEdge[0], clipEdge[1], E)
							print "2: Clip intersection not found: ClipEdge = [%s, %s], S = %s, E = %s"%(self.mvMatrix.Inverse()*clipEdge[0], self.mvMatrix.Inverse()*clipEdge[1], self.mvMatrix.Inverse()*S, self.mvMatrix.Inverse()*E)
						else:
							outputList.append(intersection)
				S = E
		#for v in outputList:
		#	print self.mvMatrix.Inverse()*v
		return outputList
	
	def clipPolygon(self, poly):
		ret = self.projectPolygon(poly)
		return self.clipToFrustum(ret)
	
	def clipMeshFace(self, face):
		return self.clipPolygon([v.pos for v in face.getVertices()])
	
	#Purpose: Return the largest face that is completely unobstructed from
	#the point of view of this beam
	#Faces contains a list of MeshFace objects to be clipped against this beam
	#Retunrs a tuple (clipped vertices, face object)
	def findFaceInFront(self, faces):
		validFaces = []
		#First find the faces that are actually within the beam
		for face in faces:
			clipped = self.clipMeshFace(face)
			if len(clipped) > 0:
				#Only consider the face if it is within the beam
				validFaces.append((clipped, face))
		faceInFront = None
		faceArea = 0.0
		for i in range(0, len(validFaces)):
			face = validFaces[i]
			#Put the clipped coordinates of this face back into world
			#coordinates and put them back on their corresponding
			#face before comparing them
			vertices = [self.mvMatrix.Inverse()*v for v in face[0]]
			for i in range(0, len(vertices)):
				ray = Ray3D(self.origin, vertices[i] - self.origin)
				v = ray.intersectMeshFace(face[1])
				if not v:
					print "ERROR: Unable to put face back into world coordinates"
				else:
					vertices[i] = v[1]
			#Check "face" against the plane of every other valid face
			for j in range(0, len(validFaces)):
				if i == j:
					continue
				otherFace = validFaces[j]
				normal = otherFace[1].getNormal()
				P0 = otherFace[1].starV.pos
				dV = P0 - self.origin
				#Make sure plane normal is pointing in the direction of this beam
				if dv.Dot(normal) < 0:
					normal = (-1)*normal
				plane = Plane3D(P0, normal)
				#Check every clipped point of face against the plane of otherFace
				allInFront = True
				for v in vertices
					if plane.distFromPlane(v) > 0:
						#One of the points is behind the plane
						allInFront = False
						break
				area = getPolygonArea(vertices)
				if area > faceArea:
					faceArea = area
					faceInFront = face
		return faceInFront
				
	
	def __str__(self):
		ret = "Beam3D: origin = %s, neardist = %s, Points = "%(self.origin, self.neardist)
		for v in self.frustVertices:
			ret = ret + "%s "%v
		return ret

if __name__== '__main__':
	origin =  Point3D(-2.5, 2.5, -2)
	frustPoints = [Point3D(1.25, 2.5, 2.5), Point3D(1.25, 2.5, -2.5), Point3D(3.75, 2.5, -2.5), Point3D(3.75, 2.5, 2.5)]
	points = [Point3D(-4.5, -3.75, 0), Point3D(0.5, -3.75, 0), Point3D(0.5, -6.25, 0), Point3D(-4.5, -6.25, 0)]
	beam = Beam3D(origin, frustPoints)
	beam.clipPolygon(points)

if __name__ == '__main__old':
	mesh = getRectMesh(Point3D(-1, -1, -1), Point3D(-1, 1, -1), Point3D(0, 1, -1), Point3D(0, -1, -1))
	beam = Beam3D(Point3D(0, 0, 0), [v.pos for v in mesh.faces[0].getVertices()], mesh.faces[0])
	#poly = [Vector3D(-3, 0, 0), Vector3D(0, 0, 1), Vector3D(2, 0, 1), Vector3D(3, 0, 0), Vector3D(7, 0, -4), Vector3D(5, 0, -5), Vector3D(3, 0, -5), Vector3D(0, 0, -3)]
	#poly = [Vector3D(-1, 0, -1)]#, Vector3D(-0.5, 0.5, -1), Vector3D(1.5, 0.5, -1), Vector3D(2, 0, -1), Vector3D(1.5, -0.5, -1), Vector3D(0, -1, -1)]
	#poly = [v+Vector3D(-100, 0, 0) for v in poly]
	poly = [Point3D(-1, -1, -1), Point3D(-1, 1, -1), Point3D(0, 1, -1), Point3D(0, -1, -2)]
	poly = beam.projectPolygon(poly)
	poly = beam.clipToFrustum(poly)
	for v in poly:
		print beam.mvMatrix.Inverse()*v