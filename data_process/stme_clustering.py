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


def get_noise_index_list(df_col, coord_list):
    """
    :param df_col: 当前 dataFrame 中 ‘cluster’ 列的标签数据(已转换成列表)，元素是 number 类型
    :param coord_list: 当前 坐标列表
    :return 返回 所有噪声点在 coords 中的索引，所有噪声点坐标
    """
    noise_index_lst = []
    noise_coord_lst = []
    lst = df_col
    for i, label in enumerate(lst):
        if label == -1:
            noise_index_lst.append(i)
            noise_coord_lst.append(coord_list[i])
    return noise_index_lst, noise_coord_lst


def stme_ones(coord_list, start_cluster_idx):
    dataframe = pd.DataFrame({'lat': coord_list[:, 0], 'lon': coord_list[:, 1], 'type': -1, 'cluster': 0})
    dataframe, clusterDensityList_nor, num_of_clusters = STME(dataframe, k=k, kt=kt, t_window=86400, min_pts=min_pts)
    print('stme_ones\n', dataframe['cluster'].values.tolist())
    labels = dataframe['cluster'].values.tolist()
    labels = [x + start_cluster_idx if x != -1 else x for x in labels]
    dataframe['cluster'] = np.array(labels)
    print(dataframe['cluster'].values.tolist())
    return dataframe, clusterDensityList_nor, num_of_clusters


def stme_iteration(coord_list, total_step):
    """
    :param coord_list 总的要聚类的点列表
    :param total_step 第一次聚类后，需要继续聚类的次数，即总聚类次数为 total_step + 1
    :return total_df 总的聚类得到的 dataFrame, total_num_clusters 聚类的簇的个数 (最大簇 id + 1)
    """
    start_cluster_idx = 0  # 每轮聚类开始的簇的编号
    total_num_clusters = 0
    total_df, clusterDensityList_nor, num_of_clusters = stme_ones(coord_list, start_cluster_idx)
    total_cluster_labels = total_df['cluster'].values.tolist()  # 总的聚类簇 id 列表
    # 第一轮聚类得到的噪声数组、噪声点在原数组的索引列表
    noise_index, cur_noise_coords = get_noise_index_list(total_cluster_labels, coord_list)

    for i in range(total_step):
        # 聚类时要计算 k 邻近，因此输入的点个数不能小于 k
        if len(cur_noise_coords) < k:
            break
        print('当前剩余噪声点个数: ', len(cur_noise_coords))
        start_cluster_idx = max(total_df['cluster']) + 1
        # 本轮聚类的对象是上次聚类中的噪声点，聚类的初始簇 id 是 上次聚类最大 id + 1 （start_cluster_idx）
        cur_df, clusterDensityList_nor, num_of_clusters = stme_ones(np.array(cur_noise_coords), start_cluster_idx)
        # 基于上次的噪声点数组聚类结果，计算出新的、索引与 cur_noise_coords 对应的簇 label 数组
        cur_cluster_labels = cur_df['cluster']
        # noise_index 是 cur_noise_coords 噪声点对应原点集的索引，本轮噪声聚类后，把本轮聚类结果更新到总聚类结果中
        for idx, label in enumerate(cur_cluster_labels):
            total_cluster_labels[noise_index[idx]] = label
        print('总聚类标签', total_cluster_labels)
        total_df['cluster'] = np.array(total_cluster_labels)
        # 本轮聚类后，检查剩下的噪声点，归到一个数组，并记录它们的索引，由下一轮使用
        noise_index, cur_noise_coords = get_noise_index_list(total_cluster_labels, coord_list)
        # 更新总的簇个数
        total_num_clusters = start_cluster_idx + num_of_clusters

    return total_df, total_num_clusters


def stme():
    # 纬度在前，经度在后 [latitude, longitude]
    file_info = FileInfo()
    coord_list = get_trip_endpoints(file_info, 50, False)
    coords_set = set()
    for coord in coord_list:
        lon, lat = coord[0], coord[1]
        if not str(lon) + "_" + str(lat) in coords_set:
            coords_set.add(str(lon) + "_" + str(lat))

    coord_list = np.array(coord_list)
    dataframe = pd.DataFrame({'lat': coord_list[:, 0], 'lon': coord_list[:, 1], 'type': -1, 'cluster': 0})

    print("参数: k： " + str(k) + " kt: " + str(kt) + " min_pts: " + str(min_pts))
    dataframe, clusterDensityList_nor, num_of_clusters = STME(dataframe, k=k, kt=kt, t_window=86400, min_pts=min_pts)  # 0.0381 751
    # earth's radius in km
    label_of_clusters = dataframe['cluster']
    ratio = len(label_of_clusters[label_of_clusters[:] == -1]) / len(label_of_clusters)  # 计算噪声点个数占总数的比例
    # num_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)  # 获取分簇的数目
    print('ratio:' + str(ratio))
    print('Clustered ' + str(len(coord_list)) + ' points to ' + str(num_of_clusters) + ' clusters')
    dataframe.to_csv("../spatio_splits/spatio_point_split_" + str(k) + "_" + str(kt) + "_" + str(min_pts) + ".csv")

    # print('coords', coords)
    # 所有簇的点组成的面
    hulls = []
    figure = plt.figure(figsize=(20, 10))
    axis = figure.subplots()
    for p in coord_list[label_of_clusters == -1]:
        x, y = p[0], p[1]
        axis.scatter(x, y, c='#000', marker='o', s=10)
    for n in range(num_of_clusters):
        # print(n, coords[cluster_labels == n + 1])
        points = []
        cur_color = randomcolor()
        for p in coord_list[label_of_clusters == n + 1]:
            x, y = p[0], p[1]
            points.append(Point(x, y))
            axis.scatter(x, y, c=cur_color, marker='o', s=10)
        # points = [Point(i, j) for i, j in coords[cluster_labels == n + 1]]
        multi_points = MultiPoint(points)
        hulls.append(multi_points.convex_hull)

    axis.set_xlabel('lon')  # 画出坐标轴
    axis.set_ylabel('lat')
    plt.savefig(f'../../figs/k{k}_kt{kt}_mpts{min_pts}.png')
    plt.show()
    return hulls


if __name__ == "__main__":
    # hulls = stme()
    # print(hulls)
    fileInfo = FileInfo()
    coords = get_trip_endpoints(fileInfo, 50, False)
    coords = np.array(coords)
    df, num_clusters = stme_iteration(coords, 4)
    print(f'簇个数：{num_clusters}')
    cluster_labels = df['cluster']
    fig = plt.figure(figsize=(20, 10))
    ax = fig.subplots()
    print(coords.shape, cluster_labels.shape)
    for p in coords[cluster_labels == -1]:
        x, y = p[0], p[1]
        ax.scatter(x, y, c='#000', marker='o', s=10)
    for n in range(num_clusters):
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
    plt.savefig(f'../../figs/迭代聚类_k{k}_kt{kt}_mpts{min_pts}.png', dpi=300)
    plt.show()
    # return hulls
