# Visualize the clustering
import json

import numpy as np
from matplotlib import pyplot as plt
from sklearn.cluster import AgglomerativeClustering
from time import time
from sklearn import preprocessing
from sklearn import manifold, datasets

from poi_process.read_poi import getPOI_Coor
from trip_process.read_trips import getTrips
from vis.trajectoryVIS import FileInfo


def plot_clustering(X_red, X, labels, title=None):
    x_min, x_max = np.min(X_red, axis=0), np.max(X_red, axis=0)
    X_red = (X_red - x_min) / (x_max - x_min)

    plt.figure(figsize=(6, 4))
    for i in range(X_red.shape[0]):
        plt.text(X_red[i, 0], X_red[i, 1], str(y[i]),
                 color=plt.get_cmap('Spectral')(labels[i] / 10.),
                 fontdict={'weight': 'bold', 'size': 9})

    plt.xticks([])
    plt.yticks([])
    if title is not None:
        plt.title(title, size=17)
    plt.axis('off')
    plt.tight_layout()


def get_trip_endpoints(fileInfo, filter_step, use_cell):
    points = []
    trips, lines = getTrips(fileInfo, filter_step, use_cell)
    for index, trip in enumerate(trips):
        points.append(trip[0])
        points.append(trip[-1])
    return points


# 2D embedding of the digits dataset
if __name__ == "__main__":
    fileInfo = FileInfo()
    points = get_trip_endpoints(fileInfo, 50, False)
    min_max_scaler = preprocessing.MinMaxScaler()
    points = min_max_scaler.fit_transform(points)
    print("Computing embedding")

    linkage = 'average'
    clustering = AgglomerativeClustering(linkage=linkage, affinity='euclidean' , n_clusters=150) # , n_clusters=5
    t0 = time()
    clustering.fit(points)
    labels = clustering.fit_predict(points)
    print('labels', labels, len(labels))
    print("%s : %.2fs" % (linkage, time() - t0))

    plt.scatter(points[:, 0], points[:, 1], c=labels, s=5)
    plt.show()

    # with open("../conf/graph_gen.json") as conf:
    #     json_data = json.load(conf)
    #     fileInfo.poi_dir = json_data['poi_dir']
    #     fileInfo.poi_file_name_lst = json_data['poi_file_name_lst']
    #     X = getPOI_Coor(fileInfo.poi_dir, fileInfo.poi_file_name_lst)
    #     min_max_scaler = preprocessing.MinMaxScaler()
    #     data_M = min_max_scaler.fit_transform(X)
    #     # n_samples, n_features = X.shape
    #
    #     np.random.seed(0)
    #     print("Computing embedding")
    #     # X_red = manifold.SpectralEmbedding(n_components=2).fit_transform(X)
    #     # print(X_red)
    #     # print("Done.")
    #
    #     # for linkage in ('ward', 'average', 'complete'):
    #     linkage = 'average'
    #     clustering = AgglomerativeClustering(linkage=linkage, affinity='euclidean') # , n_clusters=5
    #     t0 = time()
    #     clustering.fit(data_M)
    #     labels = clustering.fit_predict(data_M)
    #     print("%s : %.2fs" % (linkage, time() - t0))
    #
    #     plt.scatter(data_M[:, 0], data_M[:, 1], c=labels)
    #     plt.show()
    #     # plot_clustering(X_red, X, clustering.labels_, "%s linkage" % linkage)
    #     #
    #     # plt.show()