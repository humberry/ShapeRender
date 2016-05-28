# coding: utf-8
from struct import unpack
import math, Image, ImageDraw, ImageFont, ui, scene, sys, sqlite3
from timeit import default_timer as timer
from StringIO import StringIO

class ShapeRender(object):
    def __init__(self, config):
        #start = timer()
        self.shape_type_def = {0: 'Null Shape',1: 'Point', 3: 'PolyLine', 5: 'Polygon', 8: 'MultiPoint', 11: 'PointZ', 13: 'PolyLineZ', 15: 'PolygonZ', 18: 'MultiPointZ', 21: 'PointM', 23: 'PolyLineM', 25: 'PolygonM', 28: 'MultiPointM', 31: 'MultiPatch'}
        
        #create an image depending on the screen size
        #scr = ui.get_screen_size() * scene.get_screen_scale()
        #self.scr_width = scr[0]
        #self.scr_height = scr[1] - 64.0    #title bar = 64px
        self.scr_width = config[0][0]
        self.scr_height = config[0][1]
        self.sqlcon = None
        self.sqlcur = None
        
        self.read_db()
        self.xmin = config[1][0]
        self.ymin = config[1][1]
        self.xmax = config[1][2]
        self.ymax = config[1][3]
        self.xoffset = 180.0
        self.yoffset = 90.0
        if self.xmin < 0 and self.xmax > 0:
            self.xdelta = abs(self.xmax) + abs(self.xmin)
        elif self.xmin < 0 and self.xmax < 0:
            self.xdelta = abs(self.xmin) - abs(self.xmax)
        else:
            self.xdelta = abs(self.xmax) - abs(self.xmin)
        if self.ymin < 0 and self.ymax > 0:
            self.ydelta = abs(self.ymax) + abs(self.ymin)
        elif self.ymin < 0 and self.ymax < 0:
            self.ydelta = abs(self.ymin) - abs(self.ymax)
        else:
            self.ydelta = abs(self.ymax) - abs(self.ymin)
        print str(self.xdelta) + ' / ' + str(self.ydelta)
        self.imagebuffer = None
        self.drawbuffer = None
        self.bgcolor = config[4]
        self.line_or_dot_size = None
        self.color = None
        
        if config[2][0] != None:
            self.fontcolor = config[2][1]
            self.fontsize = config[2][2]
            self.font = ImageFont.truetype(config[2][0], self.fontsize)

        self.pixel = self.scr_width / self.xdelta
        print 'pixel = ' + str(self.pixel)
        img_height = self.scr_width / (self.xdelta / self.ydelta)
        self.imagebuffer = Image.new('RGBA', (int(self.scr_width),int(img_height)), self.bgcolor)
        self.drawbuffer = ImageDraw.Draw(self.imagebuffer)
        
        if self.xmin != -180.0:
            self.xoffset = self.xmin * -1
        print 'xoffset = ' + str(self.xoffset)
        if self.ymin != -90.0:
            self.yoffset = self.ymax
        print 'yoffset = ' + str(self.yoffset)
        
        for i in range(5, len(config)):
            self.color = config[i][1]
            self.line_or_dot_size = config[i][2]
            self.read_data(config[i][0])
            
        if config[3][0] != None:
            self.color = config[3][0]
            self.line_or_dot_size = config[3][2]
            self.draw_grid(config[3][1])

        self.imagebuffer.show()
        #end = timer()
        #print 'time for select: ' + str(end-start)
        
    def draw_grid(self, gridspacing):
        ratio = self.xdelta / self.ydelta
        x_range = self.xdelta / gridspacing
        y_range = x_range / ratio
        x_start = int(self.xmin / gridspacing)
        x_end = int(x_start + x_range) + 1
        y_start = int(self.ymin / gridspacing)
        y_end = int(y_start + y_range) + 1
        if self.xmin < 0 and self.xmax > 0:
            x_start += 1
        if self.ymin < 0 and self.ymax > 0:
            y_start += 1
        #draw line to next full degree
        if self.xmin >= 0:
            full_deg_x_off = (self.xmin - (int(self.xmin) + 1)) * -1
        else:
            full_deg_x_off = (self.xmin - int(self.xmin)) * -1
        if self.ymin >= 0:
            full_deg_y_off = (self.ymin - (int(self.ymin) + 1)) * -1
        else:
            full_deg_y_off = (self.ymin - int(self.ymin)) * -1
        width, height = self.drawbuffer.textsize('0', font=self.font)
        for x in xrange(x_start,x_end):
            x1 = (gridspacing * x + self.xoffset + full_deg_x_off) * self.pixel
            y1 = ((90 - self.yoffset) * -1) * self.pixel
            x2 = (gridspacing * x + self.xoffset + full_deg_x_off) * self.pixel
            y2 = ((-90 - self.yoffset) * -1) * self.pixel
            self.drawbuffer.line(((x1,y1),(x2,y2)), fill=self.color, width=self.line_or_dot_size)
            self.drawbuffer.text((x1 + 5, 5), str(gridspacing * x), self.fontcolor, font=self.font)
        for y in xrange(y_start,y_end):
            x1 = (-180 + self.xoffset) * self.pixel
            y1 = ((gridspacing * y - self.yoffset + full_deg_y_off) * -1) * self.pixel
            x2 = (180 + self.xoffset) * self.pixel
            y2 = ((gridspacing * y - self.yoffset + full_deg_y_off) * -1) * self.pixel
            self.drawbuffer.line(((x1,y1),(x2,y2)), fill=self.color, width=self.line_or_dot_size)
            self.drawbuffer.text((5, y1 - 5 - height), str(gridspacing * y), 'black', font=self.font)
        
    def read_data(self, shapefile):
        cursor = self.sqlcur.execute("SELECT ID_Shape FROM Shapes WHERE Name = ?", (shapefile,))
        id_shape = cursor.fetchone()
        if id_shape:
            print 'Shape ID = ' + str(id_shape[0])
        else:
            print 'No id_shape'
            return
            
        cursor = self.sqlcur.execute("SELECT ID_Poly FROM Polys WHERE ID_Shape = ?",id_shape)
        id_poly = cursor.fetchall()
        min_id_poly = min(id_poly)[0]
        max_id_poly = max(id_poly)[0]
        print 'Poly IDs = ' + str(min_id_poly) + ' - ' + str(max_id_poly)
        
        cursor = self.sqlcur.execute("SELECT ShapeType FROM Polys WHERE ID_Shape = ?",id_shape)
        shape_type = cursor.fetchone()[0]
        print 'ShapeType = ' + str(shape_type)

        cursor = self.sqlcur.execute("SELECT ID_Poly, ID_Point, X, Y, Name FROM Points WHERE ID_Poly >= ? AND ID_Poly <= ? ORDER BY ID_Poly, ID_Point", (min_id_poly, max_id_poly))
        points = cursor.fetchall()
        print 'length points: ' + str(len(points))

        id_poly = min_id_poly
        drawpoints = []
        width, height = self.drawbuffer.textsize('0', font=self.font)
        for j in xrange(len(points)):
            if points[j][0] == id_poly:       
                x = (points[j][2] + self.xoffset) * self.pixel
                y = ((points[j][3] - self.yoffset) * -1) * self.pixel
                if self.shape_type_def[shape_type] == 'Point':
                    self.drawbuffer.ellipse((x - self.line_or_dot_size, y - self.line_or_dot_size, x + self.line_or_dot_size, y + self.line_or_dot_size), fill=self.color)
                    if points[j][4] != None:
                        name = (points[j][4]).decode('utf8')
                        self.drawbuffer.text((x + self.line_or_dot_size, y - height), name, self.fontcolor, font=self.font)
                else:
                    drawpoints.append((x, y))
            else:
                if self.shape_type_def[shape_type] == 'PolyLine':
                    self.drawbuffer.line(drawpoints, fill=self.color, width=self.line_or_dot_size)
                elif self.shape_type_def[shape_type] == 'Polygon':
                    self.drawbuffer.polygon(drawpoints, fill=self.color)
                else:
                    print 'ShapeType ' + str(shape_type) + ' is not supported.'
                    break
                id_poly += 1
                drawpoints = []
                x = (points[j][2] + self.xoffset) * self.pixel
                y = ((points[j][3] - self.yoffset) * -1) * self.pixel
                drawpoints.append((x, y))
            if j == len(points) - 1:
                if self.shape_type_def[shape_type] == 'PolyLine':
                    self.drawbuffer.line(drawpoints, fill=self.color, width=self.line_or_dot_size)
                elif self.shape_type_def[shape_type] == 'Polygon':
                    self.drawbuffer.polygon(drawpoints, fill=self.color)
        
    def read_db(self):
        self.sqlcon = sqlite3.connect('earth.db')
        self.sqlcur = self.sqlcon.cursor()
        
        cursor = self.sqlcur.execute("SELECT Name FROM Shapes")
        shapes = cursor.fetchall()
        if shapes:
            print shapes
        else:
            print 'No shapes'
   
if __name__ == '__main__':
    config1 = [
        (3840, 2160),                     # [0] image width, image height (will be adjusted)
        # whole world
        (-180.0, -90.0, 180.0, 90.0),     # [1] xmin (smallest longitude), ymin (smallest latitude),
                                          #     xmax (biggest longitude),  ymax (biggest latitude)
        ('Arial', 'black', 40),           # [2] font, font color, font size
        (None, None, None),               # [3] grid color, grid spacing, linewidth
        #('black', 30, 2),                # [3] grid color, grid spacing, linewidth
        'lightblue',                      # [4] image background color
        ('ne_50m_land', 'brown', 1)]      # [5] tuple (shape, color, linewidth or dotsize)
        # config[0] - config[5] is mandatory

    config2 = [
        (3840, 2160),                     # [0] image width, image height
        # USA
        (-129.8, 22.7, -63.5, 49.7),      # [1] xmin, ymin, xmax, ymax
        ('Arial', 'black', 40),           # [2] font, font color, font size
        #('black', 5, 2),                  # [3] grid color, grid spacing, linewidth
        (None, None, None),               # [3] grid color, grid spacing, linewidth
        'white',                          # [4] image background color
        ('ne_50m_coastline', 'black', 1), # [5] (shape, color, line-/dotsize)
        ('ne_50m_urban_areas', 'lightgreen', 1),               # [6] next shape
        ('ne_50m_lakes', 'lightblue', 1),                      # [7] next shape
        ('ne_50m_populated_places_simple', 'red', 5),          # [8] next shape
        ('ne_50m_admin_0_boundary_lines_land', 'red', 2)]      # [9] next shape

    config3 = [
        (3840, 2160),                     # [0] image width, image height
        # Europe
        (-15.4, 35.0, 37.5, 72.0),        # [1] xmin, ymin, xmax, ymax
        ('Arial', 'black', 40),           # [2] font, font color, font size
        ('black', 5, 2),                  # [3] grid color, grid spacing, linewidth
        'white',                          # [4] image background color
        ('ne_50m_coastline', 'black', 2), # [5] (shape, color, line-/dotsize)
        ('ne_50m_land', 'lightyellow', 1),                     # [6] next shape
        ('ne_50m_admin_0_boundary_lines_land', 'red', 2),      # [7] next shape
        ('ne_50m_urban_areas', 'lightgreen', 1),               # [8] next shape
        ('ne_50m_populated_places_simple', 'red', 5)]          # [9] next shape
        
    ShapeRender(config1)
