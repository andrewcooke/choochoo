from math import floor


# https://trac.osgeo.org/postgis/wiki/UsersWikiplpgsqlfunctionsDistance
def utm_srid(lat, lon):
    return (32600 if lat > 0 else 32700) + floor((lon + 180) / 6) + 1
