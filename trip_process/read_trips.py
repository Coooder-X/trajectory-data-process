import pickle

import h5py
import numpy as np

from data_process.SpatialRegionTools import gps2vocab, gps2cell, cell2coord


def trip2seq(region, trj_data):
    seq = []
    for (lon, lat) in trj_data:
        # 不在范围的点会变成UNK
        seq.append(gps2vocab(region, lon, lat))
    return seq


def getTrips(fileInfo, filter_step, use_cell=False):
    data_path = fileInfo.trj_data_path
    data_date = fileInfo.trj_data_date
    file_name = fileInfo.trj_file_name
    file_path = data_path + data_date + '/' + file_name

    with open("../data/region.pkl", 'rb') as file:
        region = pickle.loads(file.read())

    # '../make_data/20200101_jianggan.h5'
    with h5py.File(file_path, 'r') as f:
        with h5py.File("../data/hangzhou-vocab-dist-cell250.h5") as kf:
            print('轨迹数: ', len(f['trips']))
            trips = []
            lines = []
            for i in range(0, len(f['trips']), filter_step):  # , 1600):
                locations = f['trips'][str(i + 1)]
                trip = []
                line = []
                for (lon, lat) in locations:
                    trip.append([lon, lat])
                # 将 GPS经纬度表示的轨迹 转换为 网格点经纬度表示
                if use_cell:
                    for idx, (lon, lat) in enumerate(trip):
                        cell = gps2cell(region, lon, lat)
                        x, y = cell2coord(region, cell)
                        trip[idx] = [x, y]
                # print(trip)
                for j in range(len(trip) - 1):
                    line.append([(trip[j][0], trip[j][1]), (trip[j + 1][0], trip[j + 1][1])])
                lines.append(line)
                trip = np.array(trip)
                trips.append(trip)

            return trips, lines
