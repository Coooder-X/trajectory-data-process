import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from shapely.geometry import Point, MultiPoint, GeometryCollection

from data_process.hierarchical_clustering import get_trip_endpoints
from stme_module import STME
from vis.trajectoryVIS import FileInfo, randomcolor

k = 20  # 20
kt = 10  # 10
min_pts = 20


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
    plt.show()
    return hulls


if __name__ == "__main__":
    hulls = stme()
    print(hulls)