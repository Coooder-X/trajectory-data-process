from datetime import datetime

import numpy as np  # version 1.17.2
from scipy.spatial import Delaunay  # version 1.4.1
import matplotlib.pyplot as plt  # version 3.1.2

from data_process.hierarchical_clustering import get_trip_endpoints
from poi_process.read_poi import getPOI_Coor, lonlat2meters_poi, buildKDTree
from vis.trajectoryVIS import FileInfo, randomcolor


def get_data():
    fileInfo = FileInfo()
    return get_trip_endpoints(fileInfo, 24, False)


def create_delauney(points):
    """
    :param points:  npArray 类型的轨迹端点数组（暂不包含时间）
    :return:        scipy.spatial.Delaunay 创建的三角剖分对象
    """
    # create a Delauney object using (x, y)
    tri = Delaunay(points)

    # paint a triangle
    # plt.triplot(points[:, 0], points[:, 1], tri.simplices.copy(), c='black')
    # plt.plot(points[:, 0], points[:, 1], 'o', c='green')
    # plt.axis('equal')
    # plt.show()
    return tri


def create_delaunay_graph(tri, points):
    """
    :param tri:     scipy.spatial.Delaunay 创建的三角剖分对象
    :param points:  npArray 类型的轨迹端点数组（暂不包含时间）
    :return:        返回三角剖分得到的图的邻接表. [[[to_i, dist_i], [[to_j, dist_j]], [...], ...] (无向图，双向边)
    """
    # print(tri.vertex_neighbor_vertices)
    adj_list = []
    (indptr, indices) = tri.vertex_neighbor_vertices
    for k in range(len(points)):
        to_index = indices[indptr[k]:indptr[k + 1]]
        cur_point_adj = [[to, 0] for to in to_index]
        adj_list.append(cur_point_adj)
    return adj_list


def cal_adj_dist(adj_list, od_kdtree, od_points, k):
    """
    :param adj_list:    距离全为 0 的邻接表
    :param od_kdtree:   od 点构成的 kdtree
    :param od_points:   od 点数组
    :param k:           计算 k 邻近的参数 k
    :return:            adj_list: 返回添加完距离属性的三角剖分邻接表, edge_lst: 三角剖分的边数组，每个原素是元组：(from, to, dist)
    """
    edge_lst = []
    for (a_idx, adj_point) in enumerate(adj_list):
        for pair in adj_point:
            b_idx = pair[0]
            _, a_top_k_id = od_kdtree.query(od_points[a_idx], k)
            _, b_top_k_id = od_kdtree.query(od_points[b_idx], k)
            a_set, b_set = set(), set()
            for idx in a_top_k_id.tolist():
                a_set.add(idx)
            for idx in b_top_k_id.tolist():
                b_set.add(idx)

            dist = 1 - len(a_set.intersection(b_set)) / len(a_set.union(b_set))
            pair[1] = dist
            edge_lst.append((a_idx, b_idx, dist))

    return adj_list, edge_lst


def delaunay_clustering(k: int, theta: int, od_points: list):
    """
    :param k:           聚类参数 k，以每个点的 k 邻近计算 dist
    :param theta:       聚类参数 θ，每个簇至少 θ 个点
    :param od_points:   所有 od 点的经纬度数组 [lon, tat]
    :return:            new_point_cluster_dict, new_cluster_point_dict, 分别是点id到簇id的映射和 簇id到点id的映射
                        后者的 value 是 set 集合，包含该簇下所有的点 id
    """
    od_kdtree = buildKDTree(od_points)
    #   论文步骤1，生成三角剖分对象
    triangulation = create_delauney(od_points)
    adj_list = create_delaunay_graph(triangulation, od_points)
    # print(adj_list)
    #   论文步骤2，计算三角剖分得到的图的 邻接表 和 边数组
    adj_list, edge_lst = cal_adj_dist(adj_list, od_kdtree, od_points, k)

    point_cluster_dict = {}
    cluster_point_dict = {}

    #   论文步骤3，初始化聚类，每个 od 点都是一个簇
    for i in range(len(od_points)):
        point_cluster_dict[i] = i
        cluster_point_dict[i] = set([i])

    #   论文步骤4，三角剖分的边按升序排列
    edge_lst = sorted(edge_lst, key=lambda x: x[2])

    for edge in edge_lst:
        (src, tar, dist) = edge
        if src not in point_cluster_dict or tar not in point_cluster_dict:
            continue
        src_cluster_id = point_cluster_dict[src]
        tar_cluster_id = point_cluster_dict[tar]
        #  若两端点属于不同簇，且其中一个簇大小小于 θ，则合并 tar 所在簇到 src 所在簇，删掉 tar 所在簇
        if src_cluster_id != tar_cluster_id and \
            (len(cluster_point_dict[src_cluster_id]) < theta or len(cluster_point_dict[tar_cluster_id]) < theta):
            for p_id in cluster_point_dict[tar_cluster_id]:
                point_cluster_dict[p_id] = point_cluster_dict[src]
            cluster_point_dict[src_cluster_id] = cluster_point_dict[src_cluster_id].union(cluster_point_dict[tar_cluster_id])
            cluster_point_dict.pop(tar_cluster_id)
    # print('keys', cluster_point_dict.keys())
    # print('sets', point_cluster_dict.values())
    # print('old', point_cluster_dict, cluster_point_dict)

    new_cluster_id = 0
    new_cluster_point_dict = {}
    new_point_cluster_dict = {}
    for cluster_id in cluster_point_dict.keys():
        point_set = cluster_point_dict[cluster_id]
        new_cluster_point_dict[new_cluster_id] = set(point_set)
        for p_idx in point_set:
            new_point_cluster_dict[p_idx] = new_cluster_id
        new_cluster_id += 1
    # print('new', new_point_cluster_dict)
    # print(new_cluster_point_dict.keys())
    return new_point_cluster_dict, new_cluster_point_dict


def draw_DT_clusters(cluster_point_dict: dict, od_points: list, k: int, theta: int):
    fig = plt.figure(figsize=(20, 10))
    ax = fig.subplots()
    color_dict = {idx: randomcolor() for idx in cluster_point_dict.keys()}

    for cluster_id in cluster_point_dict.keys():
        for p_idx in cluster_point_dict[cluster_id]:
            x, y = od_points[p_idx]
            ax.scatter(x, y, c=color_dict[cluster_id], marker='o', s=4)
        # points = [Point(i, j) for i, j in coords[cluster_labels == n + 1]]
        # multipoints = MultiPoint(points)
        # hulls.append(multipoints.convex_hull)

    ax.set_xlabel('lon')  # 画出坐标轴
    ax.set_ylabel('lat')
    plt.savefig(f'../../figs/三角剖分聚类_k{k}_theta{theta}_{len(od_points)}points.png', dpi=300)
    # plt.show()


if __name__ == '__main__':
    k, theta = 10, 20
    start_time = datetime.now()
    od_points = np.asarray(lonlat2meters_poi(get_data()))
    print('pos nums', len(od_points))
    print('开始聚类')
    point_cluster_dict, cluster_point_dict = delaunay_clustering(k=k, theta=theta, od_points=od_points)
    end_time = datetime.now()
    print('结束聚类，用时: ', (end_time - start_time))
    draw_DT_clusters(cluster_point_dict, od_points, k, theta)
    draw_time = datetime.now()
    print('画图用时: ', draw_time - end_time)
