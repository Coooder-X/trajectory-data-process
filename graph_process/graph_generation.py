import numpy as np

from graph_process.Graph import Graph
from graph_process.Point import Point
from poi_process.read_poi import buildKDTree, getPOI_Coor
from trip_process.read_trips import getTrips
from utils import lonlat2meters
from vis.trajectoryVIS import FileInfo


# def is_connect(region, kdtree, points, radius):

'''
尝试只用半径范围判断两点之间的连通性
'''
# def build_graph(kdtree, total_points, input_points, trip_index, radius):
#     g = Graph()
#     result = kdtree.query_ball_point(input_points, radius)
#     points = np.asarray(total_points)
#     print('result', result)
#     for i, res in enumerate(result):
#         print('res', res)
#         nearby_points = points[res]
#         print('nearby_points', nearby_points)
#         from_point_id = trip_index[i]
#         from_point = Point(str(from_point_id), from_point_id, from_point_id, {total_points[from_point_id]})
#         g.addVertex(from_point)
#         for to_point_id in res:
#             to_point = Point(str(to_point_id), to_point_id, to_point_id, {total_points[to_point_id]})
#             g.addVertex(to_point)
#             g.addDirectLine(from_point, [to_point, ])


def point_compression(trj_point_kdtree, poi_kdtree, trj_points, poi, trj_point_vis, end2poi_dict, radius):
    for i, endpoint in enumerate(trj_points):
        if trj_point_vis[i]:
            continue
        possible_idx_set = trj_point_kdtree.query_ball_point(endpoint, radius) # 当前点半径radius范围内的所有轨迹端点，包括自己
        print('possible_set', possible_idx_set)
        print(len(possible_idx_set), len(trj_points))
        possible_set = []
        possible_poi_set = []
        for possible_index in possible_idx_set:
            if trj_point_vis[possible_index]:
                continue
            possible_set.append(trj_points[possible_index])
            possible_poi = poi_kdtree.query_ball_point(trj_points[possible_index], radius) # 找轨迹端点半径radius范围内的所有POI
            possible_poi_set.append(possible_poi)
        # intersection = 当前范围内所有poi
        for i in range(1, len(possible_poi_set)):
            tmp = list(set(possible_poi_set[i-1]).intersection(set(possible_poi_set[i])))


if __name__ == "__main__":
    fileInfo = FileInfo()
    fileInfo.trj_data_path = '../../5月/'
    fileInfo.trj_data_date = '05月01日'
    fileInfo.trj_file_name = '20200501_hz.h5'
    fileInfo.poi_dir = '../../hangzhou-POI'
    fileInfo.poi_file_name_lst = ['商务住宅.xlsx', '风景名胜.xlsx']

    filter_step = 50
    use_cell = False
    trips, lines = getTrips(fileInfo, filter_step, use_cell)
    trip_index = [i for i in range(len(trips))]
    endpoints = []
    for trip in trips:  # 将轨迹起点和终点转换成米单位的坐标，存入kdtree，便于通过半径查找点
        x, y = lonlat2meters(trip[0][0], trip[0][1])
        endpoints.append([x, y])
        x, y = lonlat2meters(trip[-1][0], trip[-1][1])
        endpoints.append([x, y])
    trj_point_kdtree = buildKDTree(endpoints)

    poi = getPOI_Coor(fileInfo.poi_dir, fileInfo.poi_file_name_lst)
    poi_kdtree = buildKDTree(poi)
    trj_point_vis = [False for i in range(len(endpoints))]
    end2poi_dict = {}
    radius = 1000
    point_compression(trj_point_kdtree, poi_kdtree, endpoints, poi, trj_point_vis, end2poi_dict, radius)

    # for trip in trips: # 将轨迹起点和终点转换成米单位的坐标，分别存入kdtree，便于通过半径查找点
    #     time1, time2 = trip[0][2], trip[-1][2]
    #     x1, y1 = lonlat2meters(trip[0][0], trip[0][1])
    #     p1 = [x1, y1]
    #     x2, y2 = lonlat2meters(trip[-1][0], trip[-1][1])
    #     p2 = [x2, y2]
    #     if time1 < time2:
    #         start_points.append(p1)
    #         end_points.append(p2)
    #     else:
    #         start_points.append(p2)
    #         end_points.append(p1)
    # start_kdtree = buildKDTree(start_points)
    # end_kdtree = buildKDTree(end_points)

    # radius = 2000
    # build_graph(start_kdtree, start_points, end_points, trip_index, radius)
