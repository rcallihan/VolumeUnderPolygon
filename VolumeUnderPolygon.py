#Takes measures volume underneath polygon, above DEM. Original model by Jude Kastens. Interpreted in python by Ryan Callihan.

# Imports, license checkouts
import arcpy, os, sys, traceback, exceptions, re
from arcpy.sa import *
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("spatial")

#Input Parameters 
OutputLocation = r"C:\Users\IEUser\Desktop\playafiles\VolTest"
Elevation_Raster = "C:\Users\IEUser\Desktop\playafiles\lidar_huc12_extract1.img"
Gulley_Boundary_Polygon = "C:\Users\IEUser\Desktop\playafiles\VolTest\single_playa2.shp"

# Set Geoprocessing environments
arcpy.env.snapRaster = Elevation_Raster
arcpy.env.cellSize = Elevation_Raster
arcpy.env.overwriteOutput = True

#get env sell size, spatial reference
sr = arcpy.Describe(Elevation_Raster).spatialReference
CellSizeResult = arcpy.GetRasterProperties_management(Elevation_Raster, "CELLSIZEX")
Cellsize = CellSizeResult.getOutput(0)

#set workspace
arcpy.env.workspace = OutputLocation

try:
	arcpy.DeleteField_management(Gulley_Boundary_Polygon, "Volume")
	arcpy.FeatureToRaster_conversion(Gulley_Boundary_Polygon, "FID", "Gully_Mask_Raster.img", Cellsize)

	#Convert Poly verticies to points, extract raster value to poly points, convert poly to raster
	arcpy.FeatureVerticesToPoints_management(Gulley_Boundary_Polygon, "Gulley_Boundary_Points.shp", "ALL")
	ExtractValuesToPoints("Gulley_Boundary_Points.shp", Elevation_Raster, "Gully_Points_with_Elevation.shp", "NONE", "VALUE_ONLY")

	output_tin = OutputLocation + "/Poly_Boundary_Tin"
	arcpy.CreateTin_3d(output_tin, sr, "Gully_Points_with_Elevation.shp RASTERVALU masspoints", "DELAUNAY")

	#Tin to raster
	TinRastCellSize = "CELLSIZE " + Cellsize
	arcpy.TinRaster_3d(output_tin, "cap_raster", "FLOAT", "", TinRastCellSize, "")

	#sets elevation pixels outside of polygon of interest to null.  
	outElevationraster = SetNull((IsNull("Gully_Mask_Raster.img")), Elevation_Raster)
	#Ignore pixels with negative depth values
	outDepthraster = Con("cap_raster" > outElevationraster, "cap_raster" - outElevationraster)
	
	#calculates volume above raster, adds output to the poly shp
	arcpy.SurfaceVolume_3d(outDepthraster, '', 'ABOVE')
	result = arcpy.GetMessages()
	volume = float(re.findall(r'Volume= *([\d\.]+)', result)[0])
	arcpy.AddField_management(Gulley_Boundary_Polygon, "Volume", "FLOAT", "15", "4")
	arcpy.CalculateField_management(Gulley_Boundary_Polygon, "Volume", float(volume))
	print volume

except arcpy.ExecuteError:
	print arcpy.GetMessages()
except:
	tb = sys.exc_info()[2]
	tbinfo = traceback.format_tb(tb)[0]
	pymsg = 'PYTHON ERRORS:\nTraceback info:\n{0}\nError Info:\n{1}'\
		.format(tbinfo, str(sys.exc_info()[1]))
	msgs = 'ArcPy ERRORS:\n {0}\n' .format(arcpy.GetMessages(2))
	arcpy.AddError(pymsg)
	arcpy.AddError(msgs)