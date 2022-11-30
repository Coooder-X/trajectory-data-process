import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from shapely.geometry import Point, MultiPoint, GeometryCollection

from data_process.hierarchical_clustering import get_trip_endpoints
from stme_module import STME
from vis.trajectoryVIS import FileInfo, randomcolor

# k = 15 kt = 10 min_pts = 10  92 clusters
# k = 15 kt = 8 min_pts = 10  83 clusters
# k = 12 kt = 8 min_pts = 10  72 clusters   簇小 多
# k = 12 kt = 6 min_pts = 7  88 clusters
# k = 12 kt = 6 min_pts = 9  125 clusters   目前最优
k = 12  # 20
kt = 5  # 10
min_pts = 10


def stme_ones(coords, start_cluster_idx):
    df = pd.DataFrame({'lat': coords[:, 0], 'lon': coords[:, 1], 'type': -1, 'cluster': start_cluster_idx})
    df, clusterDensityList_nor, num_clusters = STME(df, k=k, kt=kt, t_window=86400, min_pts=min_pts)  # 0.0381 751
    return df, clusterDensityList_nor, num_clusters


def stme_iteration(coords, total_step):
    start_cluster_idx = 0
    total_cluster_labels = []
    total_num_clusters = 0
    total_df, clusterDensityList_nor, num_clusters = stme_ones(coords, start_cluster_idx)
    cur_cluster_labels = total_df['cluster']
    total_cluster_labels.extend(cur_cluster_labels)
    cur_noise_coords = coords[cur_cluster_labels == -1]
    for i in range(total_step):
        print('当前剩余噪声点个数: ', cur_noise_coords)
        start_cluster_idx = max(cur_cluster_labels)
        cur_df, clusterDensityList_nor, num_clusters = stme_ones(cur_noise_coords, start_cluster_idx)
        cur_cluster_labels = cur_df['cluster']
        cur_noise_coords = coords[cur_cluster_labels == -1]

        total_df.concat([total_df, cur_df], axis=0)
        total_cluster_labels.extend(cur_cluster_labels)
        total_num_clusters = max(total_num_clusters, num_clusters)
    return total_df, total_num_clusters, total_num_clusters


def stme():
    ## 纬度在前，经度在后 [latitude, longitude]
    fileInfo = FileInfo()
    coords = get_trip_endpoints(fileInfo, 50, False)
    coords_set = set()
    for coord in coords:
        lon, lat = coord[0], coord[1]
        if not str(lon) + "_" + str(lat) in coords_set:
            coords_set.add(str(lon) + "_" + str(lat))

    coords = np.array(coords)
    df = pd.DataFrame({'lat': coords[:, 0], 'lon': coords[:, 1], 'type': -1, 'cluster': 0})

    print("参数: k： " + str(k) + " kt: " + str(kt) + " min_pts: " + str(min_pts))
    df, clusterDensityList_nor, num_clusters = STME(df, k=k, kt=kt, t_window=86400, min_pts=min_pts)  # 0.0381 751
    # earth's radius in km
    cluster_labels = df['cluster']
    raito = len(cluster_labels[cluster_labels[:] == -1]) / len(cluster_labels)  # 计算噪声点个数占总数的比例
    # num_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)  # 获取分簇的数目
    print('rattio:' + str(raito))
    print('Clustered ' + str(len(coords)) + ' points to ' + str(num_clusters) + ' clusters')
    df.to_csv("../spatio_splits/spatio_point_split_" + str(k) + "_" + str(kt) + "_" + str(min_pts) + ".csv")

    # print('coords', coords)
    # 所有簇的点组成的面
    hulls = []
    fig = plt.figure(figsize=(20, 10))
    ax = fig.subplots()
    for p in coords[cluster_labels == -1]:
        x, y = p[0], p[1]
        ax.scatter(x, y, c='#000', marker='o', s=10)
    for n in range(num_clusters):
        # print(n, coords[cluster_labels == n + 1])
        points = []
        color = randomcolor()
        for p in coords[cluster_labels == n + 1]:
            x, y = p[0], p[1]
            points.append(Point(x, y))
            ax.scatter(x, y, c=color, marker='o', s=10)
        # points = [Point(i, j) for i, j in coords[cluster_labels == n + 1]]
        multipoints = MultiPoint(points)
        hulls.append(multipoints.convex_hull)

    ax.set_xlabel('lon')  # 画出坐标轴
    ax.set_ylabel('lat')
    plt.savefig(f'../../figs/k{k}_kt{kt}_mpts{min_pts}.png')
    plt.show()
    return hulls


if __name__ == "__main__":
    # hulls = stme()
    # print(hulls)
    fileInfo = FileInfo()
    coords = get_trip_endpoints(fileInfo, 50, False)
    coords = np.array(coords)
    df, cluster_labels, num_clusters = stme_iteration(coords, 3)
    fig = plt.figure(figsize=(20, 10))
    ax = fig.subplots()
    for p in coords[cluster_labels == -1]:
        x, y = p[0], p[1]
        ax.scatter(x, y, c='#000', marker='o', s=10)
    for n in range(num_clusters):
        # print(n, coords[cluster_labels == n + 1])
        points = []
        color = randomcolor()
        for p in coords[cluster_labels == n + 1]:
            x, y = p[0], p[1]
            points.append(Point(x, y))
            ax.scatter(x, y, c=color, marker='o', s=10)
        # points = [Point(i, j) for i, j in coords[cluster_labels == n + 1]]
        multipoints = MultiPoint(points)
        # hulls.append(multipoints.convex_hull)

    ax.set_xlabel('lon')  # 画出坐标轴
    ax.set_ylabel('lat')
    # plt.savefig(f'../../figs/k{k}_kt{kt}_mpts{min_pts}.png')
    plt.show()
    # return hulls