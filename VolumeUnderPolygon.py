#Takes measures volume underneath polygon, above DEM. Original model by Jude Kastens. Interpreted in python by Ryan Callihan.

# Imports, license checkouts
import arcpy, os, sys, traceback, exceptions, re
from arcpy.sa import *
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#Input Parameters 
# OutputLocation = r"C:\Users\IEUser\Desktop\playafiles\VolTest"
# Elevation_Raster = "C:\Users\IEUser\Desktop\playafiles\lidar_huc12_extract1.img"
# Input_Polygon_Shp = "C:\Users\IEUser\Desktop\playafiles\VolTest\single_playa2.shp"

#input from Arc Toolbox. Comment out below and uncomment above if wanting a stand-a-lone script. 
OutputLocation = arcpy.GetParameterAsText(0)
Elevation_Raster = arcpy.GetParameterAsText(1)
Input_Polygon_Shp = arcpy.GetParameterAsText(2)

#set Geoprocessing environments
arcpy.env.snapRaster = Elevation_Raster
arcpy.env.cellSize = Elevation_Raster
arcpy.env.overwriteOutput = True
arcpy.env.workspace = OutputLocation

#Convert input poly shp to feature layer, get poly count, and add fields
Polygon_Layer = "Polygon_Layer"
arcpy.MakeFeatureLayer_management(Input_Polygon_Shp, Polygon_Layer)
PolyCount = int(arcpy.GetCount_management(Polygon_Layer).getOutput(0))
arcpy.DeleteField_management(Polygon_Layer, "Volume")
arcpy.AddField_management(Polygon_Layer, "Volume", "FLOAT", "15", "4")
loopcount = 0

#get env cell size, spatial reference
sr = arcpy.Describe(Elevation_Raster).spatialReference
CellSizeResult = arcpy.GetRasterProperties_management(Elevation_Raster, "CELLSIZEX")
Cellsize = CellSizeResult.getOutput(0)

field = "FID"
cursor = arcpy.SearchCursor(Polygon_Layer)
row = cursor.next()
while row:
	rowFID = row.getValue(field)
	loopcount = loopcount + 1
	query = '"FID" = ' + str(rowFID) 
	arcpy.SelectLayerByAttribute_management(Polygon_Layer, "NEW_SELECTION", query)

	arcpy.AddMessage("======================================")
	arcpy.AddMessage("Calculating volume for polygon %s of %s" % (loopcount, PolyCount))
	arcpy.AddMessage("======================================")

	arcpy.FeatureToRaster_conversion(Polygon_Layer, "FID", "Poly_Mask", Cellsize)

	#Convert Poly verticies to points, extract raster value to poly points, convert poly to raster
	arcpy.AddMessage("Converting polygon verticies to points...")
	arcpy.FeatureVerticesToPoints_management(Polygon_Layer, "Poly_Boundary_Points.shp", "ALL")
	arcpy.AddMessage("Extracting elevation values from elevation raster...")
	ExtractValuesToPoints("Poly_Boundary_Points.shp", Elevation_Raster, "Poly_Points_with_Elevation.shp", "NONE", "VALUE_ONLY")

	#converts raster with elevation points to a TIN. 
	#output_tin = OutputLocation + "/Poly_Boundary_Tin"
	arcpy.AddMessage("Creating TIN and converting to raster...")
	arcpy.CreateTin_3d("Poly_Boundary_Tin", sr, "Poly_Points_with_Elevation.shp RASTERVALU masspoints", "DELAUNAY")

	#Tin to raster
	TinRastCellSize = "CELLSIZE " + Cellsize
	arcpy.TinRaster_3d("Poly_Boundary_Tin", "cap_raster", "FLOAT", "", TinRastCellSize, "")

	#sets elevation pixels outside of polygon of interest to null. Ignore pixels with negative depth values 
	arcpy.AddMessage("Raster calculator...setting non area of interest to null...")
	outElevationraster = SetNull((IsNull("Poly_Mask")), Elevation_Raster)
	arcpy.AddMessage("Raster calculator...ignoring pixels with negative depth values...")
	outDepthraster = Con("cap_raster" > outElevationraster, "cap_raster" - outElevationraster)
	
	#calculates volume above raster, adds output to the poly shp
	arcpy.AddMessage("Calculating volume and adding value to polygon shapefile...")
	arcpy.SurfaceVolume_3d(outDepthraster, '', 'ABOVE')
	result = arcpy.GetMessages()
	volume = float(re.findall(r'Volume= *([\d\.]+)', result)[0])
	arcpy.CalculateField_management(Polygon_Layer, "Volume", volume)
	
	row = cursor.next()

arcpy.AddMessage("Cleaning up intermediate files...")
for filename in ["Poly_Boundary_Points.shp", "Poly_Points_with_Elevation.shp", "Poly_Boundary_Tin", 
				outElevationraster, outDepthraster, "cap_raster", "Poly_Mask"]:
	if arcpy.Exists(filename):
		arcpy.Delete_management(filename)

arcpy.AddMessage("======================================")
arcpy.AddMessage("Done!")
arcpy.AddMessage("======================================")


