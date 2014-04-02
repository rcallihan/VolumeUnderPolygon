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

#in put from Arc Toolbox. Comment out below and uncomment above if wanting a stand-a-lone script. 
OutputLocation = arcpy.GetParameterAsText(0)
Elevation_Raster = arcpy.GetParameterAsText(1)
Input_Polygon_Shp = arcpy.GetParameterAsText(2)

#set Geoprocessing environments
arcpy.env.snapRaster = Elevation_Raster
arcpy.env.cellSize = Elevation_Raster
arcpy.env.overwriteOutput = True
arcpy.env.workspace = OutputLocation

#get env sell size, spatial reference
sr = arcpy.Describe(Elevation_Raster).spatialReference
CellSizeResult = arcpy.GetRasterProperties_management(Elevation_Raster, "CELLSIZEX")
Cellsize = CellSizeResult.getOutput(0)

try:
	arcpy.DeleteField_management(Input_Polygon_Shp, "Volume")
	arcpy.FeatureToRaster_conversion(Input_Polygon_Shp, "FID", "Poly_Mask", Cellsize)

	#Convert Poly verticies to points, extract raster value to poly points, convert poly to raster
	arcpy.FeatureVerticesToPoints_management(Input_Polygon_Shp, "Poly_Boundary_Points.shp", "ALL")
	ExtractValuesToPoints("Poly_Boundary_Points.shp", Elevation_Raster, "Poly_Points_with_Elevation.shp", "NONE", "VALUE_ONLY")

	#converts raster with elevation points to a TIN. 
	#output_tin = OutputLocation + "/Poly_Boundary_Tin"
	arcpy.CreateTin_3d("Poly_Boundary_Tin", sr, "Poly_Points_with_Elevation.shp RASTERVALU masspoints", "DELAUNAY")

	#Tin to raster
	TinRastCellSize = "CELLSIZE " + Cellsize
	arcpy.TinRaster_3d("Poly_Boundary_Tin" "cap_raster", "FLOAT", "", TinRastCellSize, "")

	#sets elevation pixels outside of polygon of interest to null. Ignore pixels with negative depth values 
	outElevationraster = SetNull((IsNull("Poly_Mask")), Elevation_Raster)
	outDepthraster = Con("cap_raster" > outElevationraster, "cap_raster" - outElevationraster)
	
	#calculates volume above raster, adds output to the poly shp
	arcpy.SurfaceVolume_3d(outDepthraster, '', 'ABOVE')
	result = arcpy.GetMessages()
	volume = float(re.findall(r'Volume= *([\d\.]+)', result)[0])
	arcpy.AddField_management(Input_Polygon_Shp, "Volume", "FLOAT", "15", "4")
	arcpy.CalculateField_management(Input_Polygon_Shp, "Volume", float(volume))
	
	#cleaning up intermediate files
	for filename in ["Gulley_Boundary_Points.shp", "Gully_Mask_Raster.img", "Gully_Points_with_Elevation.shp", outElevationraster, outDepthraster, "cap_raster", output_tin]:
		if arcpy.Exists(filename):
			arcpy.Delete_management(filename)
	arcpy.AddMessage("Done cleaning intermediate files.")


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

arcpy.CheckInExtension("3D")
arcpy.CheckInExtension("spatial")