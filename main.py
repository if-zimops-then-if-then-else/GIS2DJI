import os
import sys
import geopandas as gpd
import simplekml
import fiona
import xml.etree.ElementTree as ET
from shapely import Polygon, LineString, Point, MultiPolygon, \
    MultiLineString, MultiPoint
from fiona.drvsupport import supported_drivers

supported_drivers['LIBKML'] = 'rw'
software_version = 'GIS2DJI_V03'


class App:
    def toto(self, msg):
        print('print from function ' + msg)

    def create_directory(self):
        """Create a directory. Will pass if directory has been added
          by another tread."""
        if os.path.isdir('out/'):
            pass
        else:
            try:
                os.makedirs('out/')
            except WindowsError as err:
                pass
                return err

    def scan_directory(self):
        # new add multiple file extensions.  Not just one.
        extensions_lts_flt = ['.kml', '.kmz', '.shp', '.gpkg']
        file_lst = []
        for file in os.listdir('data/'):
            for q in extensions_lts_flt:
                if file.lower().endswith(q):
                    file_filter = os.path.join('data/' + file)
                    file_lst.append(file_filter)
        return file_lst

    def export_pg(self, geom, ofn, index, output_path):
        err = []
        ext = list(geom.exterior.coords)
        int_ring = []
        for interior in geom.interiors:
            int_ring.append(list(interior.coords))
        kml = simplekml.Kml()
        obj = kml.newpolygon(name=ofn,
                             description=index)
        obj.outerboundaryis = ext
        if not int_ring:
            pass
        else:
            obj.innerboundaryis = int_ring
        output_file_name = os.path.join(output_path,
                                        ofn + '-' + str(index) + '-' +
                                        geom.geom_type + '.kml')

        kml.save(output_file_name)
        err.append('Exporting: ' + output_file_name)
        return err

    def export_line(self, geom, ofn, index, output_path):
        err = []
        xyz = list(geom.coords)
        kml = simplekml.Kml()
        ofn = ofn.split('-', 1)[0]
        ofn = ofn + "-new"
        obj = kml.newlinestring(name=ofn,
                                description=index)
        obj.coords = xyz
        output_file_name = os.path.join(output_path, ofn + '.kml')

        kml.save(output_file_name)
        err.append('Exporting: ' + output_file_name)
        return err

    def export_point(self, geom, ofn, index, output_path):

        # This will export the point as a kmz.  According to the DJI api
        # documentation, points need to be kmz.
        err = []
        xyz = list(geom.coords)
        kml = simplekml.Kml()
        obj = kml.newpoint(name=ofn,
                           description=index)
        obj.coords = xyz
        output_file_name = os.path.join(output_path,
                                        ofn + '-' + str(index) + '-' +
                                        geom.geom_type + '.kmz')

        kml.savekmz(output_file_name)
        err.append('Exporting: ' + output_file_name)

        # Create PseudoWayPoint. This is a zero lenght line
        kml = simplekml.Kml()
        xyz.append(xyz[0])
        obj = kml.newlinestring(name=ofn,
                                description=index)
        obj.coords = xyz
        output_file_name = os.path.join(output_path,
                                        ofn + '-' + str(index) + '-' +
                                        'PseudoPoint' + '.kml')
        n = 1
        while os.path.isfile(output_file_name):
            output_file_name = os.path.join(output_path,
                                            ofn + '-' + str(index) + '-' +
                                            'PseudoPoint' + '(' + str(n) + ')' + '.kml')
            n += 1

        kml.save(output_file_name)
        err.append('Exporting: ' + output_file_name)
        return err

    def main_function(self, file: str, output_path):
        msg = []
        fn = os.path.basename(os.path.splitext(file)[0])  # toto.shp --> toto
        fnx = (os.path.basename(os.path.splitext(file)[1])).strip('.')  # .shp
        ffn = os.path.basename(file)  # toto.shp
        #  Load support for kml read libraries from fiona
        # gpd.io.file.fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'
        msg.append('Reading:' + ffn)
        try:
            layerlist = fiona.listlayers(file)
        except:
            msg.append('An exception occurred.' + ' Cannot read' + str(file))
            msg.append('Skipping file!')
            return

        cnt = 0
        for layers in layerlist:
            layer_name = layerlist[cnt]
            cnt += 1
            try:
                layers = gpd.read_file(file, layer=layers)
            except:
                msg.append('An exception occurred. Cannot not read layer ' + layer_name)
                msg.append('Skipping layer.')
                continue
            if len(layerlist) == 1:
                if fn == layer_name:
                    ofn = fn + '-' + fnx
                elif fn != layer_name:
                    ofn = fn + '-' + fnx + '-' + layer_name
            elif len(layerlist) > 1:
                ofn = fn + '-' + fnx + '-' + layer_name

            # Check CRS and reproject if needed
            crs = layers.crs
            if crs is None:
                msg.append(
                    layer_name + ' has no CRS (Coordinate Reference System). Output .kml will not be well georeferenced')
                msg.append('if the input file is not already in EPSG 4326 (WGS84).')
                msg.append('Resulting file may not be valid and may not open properly in drone software.')
                print(msg)

            elif crs == 'epsg:4326':
                # print('CRS for', layer_name, 'layer is EPSG 4326')
                pass
            else:
                msg.append(layer_name + ' layer has been reprojected to EPSG 4326.')
                layers = layers.to_crs(4326)

            # Iterate each row of each layers and create individual kml files
            for index, row in layers.iterrows():
                # Check if geom is valid, try to fix
                geom = row.geometry
                if geom.is_valid is True:
                    pass
                else:
                    msg.append('Invalid geometry found: Layer name = ' + '"' +
                               str(layer_name) + '"' + 'index = ' + str(index))
                    msg.append('We will try to fix the geometry...')
                    gps = (gpd.GeoSeries(geom))
                    hope4thebest = gps.make_valid()
                    geom = (hope4thebest[0])
                    msg.append('Geometry is probably fixed. Please verify.')

                if geom.geom_type == 'Polygon' or geom.geom_type == 'MultiPolygon':
                    if geom.geom_type == 'Polygon':
                        err = self.export_pg(geom, ofn, index, output_path)
                        for x in err:
                            msg.append(x)

                    elif geom.geom_type == 'MultiPolygon':
                        for parts in range(len(geom.geoms)):
                            # print (geom.geoms[parts])
                            # print (parts)
                            index_part = str(index) + '-' + str(parts)
                            err = self.export_pg(geom.geoms[parts], ofn, index_part, output_path)
                            for x in err:
                                msg.append(x)

                elif geom.geom_type == 'LineString' or \
                        geom.geom_type == 'MultiLineString':

                    if geom.geom_type == 'LineString':
                        err = self.export_line(geom, ofn, index, output_path)
                        for x in err:
                            msg.append(x)

                    elif geom.geom_type == 'MultiLineString':
                        for parts in range(len(geom.geoms)):
                            # print (geom.geoms[parts])
                            # print (parts)
                            index_part = str(index) + '-' + str(parts)
                            err = self.export_line(geom.geoms[parts], ofn, index_part, output_path)
                            for x in err:
                                msg.append(x)

                elif geom.geom_type == 'Point' or geom.geom_type == 'MultiPoint':
                    if geom.geom_type == 'Point':
                        err = self.export_point(geom, ofn, index, output_path)
                        for x in err:
                            msg.append(x)

                    elif geom.geom_type == 'MultiPoint':
                        for parts in range(len(geom.geoms)):
                            # print (geom.geoms[parts])
                            # print (parts)
                            index_part = str(index) + '-' + str(parts)
                            err = self.export_point(geom.geoms[parts], ofn, index_part, output_path)
                            for x in err:
                                msg.append(x)
                else:
                    msg.append(geom.geom_type +
                               ' is not supported. Geometry not exported')
                    continue
        return msg


if __name__ == "__main__":
    app = App()
    app.create_directory()
    files = app.scan_directory()
    for f in files:
        msg = app.main_function(f, 'out/')
        print(msg)
