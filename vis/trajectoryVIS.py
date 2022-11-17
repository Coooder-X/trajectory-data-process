import matplotlib.pyplot as plt
from matplotlib import collections as mc
from mpl_toolkits.mplot3d import Axes3D
import h5py
import random
import numpy as np
import pickle
from data_process.SpatialRegionTools import gps2vocab, gps2cell, cell2coord

import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)


def trip2seq(region, trj_data):
    seq = []
    for (lon, lat) in trj_data:
        # 不在范围的点会变成UNK
        seq.append(gps2vocab(region, lon, lat))
    return seq


def randomcolor():
    colorArr = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']
    color = ""
    for i in range(6):
        color += colorArr[random.randint(0, 14)]
    return "#" + color


colorsOfLabel = [
    "#8ECFC9", "#2878b5", "#F27970", "#A1A9D0", "#C4A5DE", "#63b2ee", "#9192ab", "#3b6291", "#bf7334", "#3b8ba1", "#ffbd66",
    "#FFBE7A", "#9ac9db", "#BB9727", "#F0988C", "#F6CAE5", "#76da91", "#7898e1", "#943c39", "#3f6899", "#c97937", "#f74d4d",
    "#FA7F6F", "#f8ac8c", "#54B345", "#B883D4", "#96CCCB", "#f8cb7f", "#efa666", "#779043", "#9c403d", "#002c53", "#2455a4",
    "#82B0D2", "#c82423", "#32B897", "#9E9E9E", "#8983BF", "#f89588", "#eddd86", "#624c7c", "#7d9847", "#ffa510", "#41b7ac",
    "#BEB8DC", "#ff8884", "#05B9E2", "#CFEAF1", "#C76DA2", "#7cd6cf", "#9987ce", "#388498", "#675083", "#0c84c6", "#E7DAD2",
    "#63b2ee", "#76da91"
]

if __name__ == "__main__":
    with open("../data/region.pkl", 'rb') as file:
        region = pickle.loads(file.read())

    fig = plt.figure(figsize=(20, 10))
    ax = fig.subplots()

    with h5py.File('../make_data/20200101_jianggan.h5', 'r') as f:
        with h5py.File("../data/hangzhou-vocab-dist-cell250.h5") as kf:
            print('轨迹数: ', len(f['trips']))
            for i in range(0, len(f['trips']), 30):  # , 1600):
                locations = f['trips'][str(i + 1)]
                trip = []
                lines = []
                for (lon, lat) in locations:
                    trip.append([lon, lat])
                seq = np.array(trip2seq(region, trip))
                # 将 GPS经纬度表示的轨迹 转换为 网格点经纬度表示
                for idx, (lon, lat) in enumerate(trip):
                    cell = gps2cell(region, lon, lat)
                    x, y = cell2coord(region, cell)
                    trip[idx] = [x, y]
                # print(trip)
                for j in range(len(trip) - 1):
                    lines.append([(trip[j][0], trip[j][1]), (trip[j + 1][0], trip[j + 1][1])])
                trip = np.array(trip)

                color = randomcolor()
                lc = mc.LineCollection(lines, colors=color, linewidths=2)
                ax.add_collection(lc)
                ax.scatter(trip[:, 0], trip[:, 1], c=color, marker='o')

            ax.set_xlabel('lon')  # 画出坐标轴
            ax.set_ylabel('lat')
            handles, labels = ax.get_legend_handles_labels()
            handle_list, label_list = [], []
            for handle, label in zip(handles, labels):
                if label not in label_list:
                    handle_list.append(handle)
                    label_list.append(label)
            plt.legend(handle_list, label_list)
            plt.show()
