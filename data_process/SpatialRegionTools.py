import random
import sys, os

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import math, pickle, os
import pandas as pd
import numpy as np
from scipy.spatial.distance import pdist
from scipy.spatial.distance import squareform
import time as T
import itertools
import h5py
from collections import Counter
from scipy import spatial
from time_utils import cfe, calAngle

UNK = 3


class SpatialRegion:
    def __init__(self, cityname, minlon, minlat, maxlon, maxlat, mintime, maxtime,
                 xstep, ystep, timestep, minfreq, maxvocab_size, k, vocab_start,
                 interesttime, nointeresttime, delta, needTime, min_length, max_length, timefuzzysize, timestart,
                 hulls, use_grid, has_label):
        # point_to_spatio, spatio_num, spatio_pos):
        self.cityname = cityname
        self.minfreq = minfreq
        self.maxvocab_size = maxvocab_size
        self.k = k
        self.vocab_start = vocab_start
        self.interesttime = interesttime
        self.nointeresttime = nointeresttime
        self.delta = delta
        self.needTime = needTime
        self.min_length = min_length
        self.max_length = max_length
        self.timefuzzysize = timefuzzysize
        self.timestart = timestart

        self.minlon = minlon
        self.minlat = minlat
        self.maxlon = maxlon
        self.maxlat = maxlat
        self.mintime = mintime
        self.maxtime = maxtime
        self.minlon = minlon
        self.xstep = xstep
        self.ystep = ystep
        self.timestep = timestep
        self.minx, self.miny = lonlat2meters(minlon, minlat)
        self.maxx, self.maxy = lonlat2meters(maxlon, maxlat)
        self.maxDis = math.sqrt(abs(self.minx - self.miny) ** 2 +
                                abs(self.maxx - self.maxy) ** 2) + 10
        self.use_grid = use_grid
        self.has_label = has_label
        # self.point_to_spatio = point_to_spatio
        # self.spatio_num = spatio_num
        # self.spatio_pos = spatio_pos
        self.hulls = hulls
        self.centers = np.array([np.array(x.centroid.coords) for x in hulls]).squeeze()
        if self.use_grid:
            self.numx = round(self.maxx - self.minx, 6) / xstep
            self.numx = int(math.ceil(self.numx))
            self.numy = round(self.maxy - self.miny, 6) / ystep
            self.numy = int(math.ceil(self.numy))
            # self.numz = 1
        # if needTime:
        #     self.numz = round(self.maxtime - self.mintime, 6) / timestep
        #     self.numz = int(math.ceil(self.numz))


def inregionT(region, lon, lat, time):
    return lon >= region.minlon and lon <= region.maxlon and \
           lat >= region.minlat and lat <= region.maxlat and \
           time >= region.mintime and time <= region.maxtime


def inregionS(region, lon, lat):
    return lon >= region.minlon and lon <= region.maxlon and \
           lat >= region.minlat and lat <= region.maxlat


def coord2cell(region, x, y):
    xoffset = round(x - region.minx, 6) / region.xstep  # todo: ?????? or ??????
    yoffset = round(y - region.miny, 6) / region.ystep
    xoffset = int(math.floor(xoffset))
    yoffset = int(math.floor(yoffset))
    return yoffset * region.numx + xoffset


def gps2cell(region, lon, lat):
    if region.use_grid:
        x, y = lonlat2meters(lon, lat)
        return coord2cell(region, x, y)
    else:
        return np.argmin(np.sum((region.centers - [lat, lon]) ** 2, 1))


def cell2coord(region, cell):
    if region.use_grid:
        yoffset = cell / region.numx
        xoffset = cell % region.numx
        y = region.miny + (yoffset + 0.5) * region.ystep
        x = region.minx + (xoffset + 0.5) * region.xstep
    else:
        (lat, lon) = region.centers[cell]
        x, y = lonlat2meters(lon, lat)
    y = (y - region.miny) / (region.maxy - region.miny)
    x = (x - region.minx) / (region.maxx - region.minx)
    return x, y


def makeVocab(region, trjfiles):
    num_out_region = 0  # ????????????????????????
    num_del_data = 0
    region.cellcount = []

    total_datas = []
    total_labels = []
    data_l = 0
    for trjfile in trjfiles:
        with h5py.File(trjfile, "r") as f:
            num = f.attrs.get("num")[0]  # ????????????????????????
            data_l += num
            for i in range(1, num + 1):
                trip = f["trips"][str(i)]  # ??? i ?????????
                if not (region.min_length <= len(trip) <= region.max_length):
                    num_del_data += 1
                    continue
                cur_trip = []
                if region.needTime:
                    timestamp = f["timestamps"][str(i)]
                    for ((lon, lat), time) in zip(trip, timestamp):
                        if not inregionT(region, lon, lat, time):
                            num_out_region += 1
                        else:
                            cur_trip.append([lon, lat, time])
                else:
                    for (lon, lat) in trip:
                        if not inregionS(region, lon, lat):
                            num_out_region += 1
                        else:
                            cur_trip.append([lon, lat])

                if not (region.min_length <= len(cur_trip) <= region.max_length):
                    num_del_data += 1
                    continue
                if region.needTime:
                    for (lon, lat, time) in cur_trip:
                        # ????????????????????????????????????cell??????
                        cell = gpsandtime2cell(region, lon, lat, time)
                        # ????????????cellpush
                        region.cellcount.append(cell)
                else:
                    for (lon, lat) in cur_trip:
                        cell = gps2cell(region, lon, lat)
                        region.cellcount.append(cell)

                total_datas.append(cur_trip)
                if region.has_label:
                    # ?????????????????????????????????
                    label = f["labels"][str(i)]  # ??? i ?????????
                    total_labels.append(int(label[()]))

                if (i % 100_000 == 1):
                    print("Process file %s: %d/%d trips" % (trjfile, i, num))

    data_l -= num_del_data
    ntrain = int(data_l * 0.8)  # ???????????????????????????
    nval = int(data_l * 0.1)
    ntest = data_l - ntrain - nval
    # shuffle = np.random.permutation(np.arange(data_l))
    # total_datas = np.array(total_datas)[shuffle]
    if not region.has_label:
        # total_labels = np.array(total_labels)[shuffle]
        # else:
        total_labels = np.zeros(len(total_datas))

    train_datas = total_datas[:ntrain]
    val_datas = total_datas[ntrain:ntrain + nval]
    test_datas = total_datas[ntrain + nval:ntrain + nval + ntest]
    train_labels = total_labels[:ntrain]
    val_labels = total_labels[ntrain:ntrain + nval]
    test_labels = total_labels[ntrain + nval:ntrain + nval + ntest]

    # for train_data in train_datas:
    #     if not region.needTime:
    #         for (lon, lat) in train_data:
    #             cell = gps2cell(region, lon, lat)
    #             region.cellcount.append(cell)
    #     else:
    #         for (lon, lat, time) in train_data:
    #             # ????????????????????????????????????cell??????
    #             cell = gpsandtime2cell(region, lon, lat, time)
    #             # ????????????cellpush
    #             region.cellcount.append(cell)

    # for trjfile in trjfiles:
    #     # ??????????????????????????????????????????????????????????????????????????????????????????????????????????????????+1
    #     with h5py.File(trjfile, "r") as f:        
    #         num = f.attrs.get("num")[0] # ????????????????????????
    #         ntrain = num * 0.8 # ???????????????????????????
    #         nval = num - ntrain
    #         if not region.needTime:
    #             for i in range(1, num):
    #                 trip = f["trips"][str(i)] # ??? i ?????????
    #                 cur_trip = []
    #                 if not (region.min_length <= len(trip) <= region.max_length):
    #                     continue
    #                 for (lon, lat) in trip:
    #                     if not inregionS(region, lon, lat):
    #                         num_out_region += 1
    #                     else:
    #                         cur_trip.append([lon, lat])
    #                 if not (region.min_length <= len(cur_trip) <= region.max_length):
    #                     continue
    #                     
    #                 for (lon, lat) in cur_trip:
    #                     cell = gps2cell(region, lon, lat)
    #                     region.cellcount.append(cell)
    #                     
    #                 trj_datas.append(cur_trip)
    #                 if region.has_label:
    #                     # ?????????????????????????????????
    #                     label = f["labels"][str(i)] # ??? i ?????????
    #                     trj_labels.append(int(label[()]))
    #                 if (i % 100_000 == 1):
    #                     print("Process file %s: %d/%d trips" % (trjfile, i, num))
    #         else:
    #             for i in range(1, num):
    #                 trip = f["trips"][str(i)] # ??? i ?????????
    #                 if not (region.min_length <= len(trip) <= region.max_length):
    #                     continue
    #                 timestamp = f["timestamps"][str(i)]
    #                 cur_trip = []
    #                 for ((lon, lat), time) in zip(trip, timestamp):
    #                     if not inregionT(region, lon, lat, time):
    #                         num_out_region += 1
    #                     else:
    #                         cur_trip.append([lon, lat, time])
    #                 if not (region.min_length <= len(cur_trip) <= region.max_length):
    #                     continue
    #                     
    #                 for (lon, lat, time) in cur_trip:
    #                     # ????????????????????????????????????cell??????
    #                     cell = gpsandtime2cell(region, lon, lat, time)
    #                     # ????????????cellpush
    #                     region.cellcount.append(cell)
    #                     
    #                 trj_datas.append(cur_trip)
    #                 if region.has_label:
    #                     # ?????????????????????????????????
    #                     label = f["labels"][str(i)] # ??? i ?????????
    #                     trj_labels.append(int(label[()]))
    #                 if (i % 100_000 == 1):
    #                     print("Process file %s: %d/%d trips" % (trjfile, i, num))
    # ???????????????????????????????????????????????????????????????????????????????????????????????????
    # ????????????????????????cell
    # ?????????????????????????????????trj_datas
    print("num_out_region:%d-------------------" % num_out_region)
    # ??????????????????????????????
    # ???????????????cell??????
    max_num_hotcells = min(region.maxvocab_size, len(region.cellcount))
    print("max_num_hotcells:%d---------------" % max_num_hotcells)
    # collet??????????????????cell??????????????????????????????????????????max???
    counts = Counter(region.cellcount).items()
    topcellcount = np.array(sorted(counts, key=lambda x: x[1], reverse=True)[1:max_num_hotcells])
    print("Cell count at min_num_hotcells:%d is %d" % (max_num_hotcells, topcellcount[-1][1]))
    print("topcellcount is %d" % (len(topcellcount)))
    # ????????????cell?????????????????????????????????
    # ???????????????????????????cell?????????????????????cell?????????first???
    a = topcellcount[:, 1] >= region.minfreq
    region.hotcell = topcellcount[topcellcount[:, 1] >= region.minfreq, 0]
    random.shuffle(region.hotcell)
    print("hotcell count is %d" % (len(region.hotcell)))
    # ??????cell???????????????????????????
    region.hotcell2vocab = dict([(cell, i + region.vocab_start)
                                 for (i, cell) in enumerate(region.hotcell)])
    region.vocab2hotcell = dict(zip(region.hotcell2vocab.values(), region.hotcell2vocab.keys()))
    # ??????size???vocab_start
    region.vocab_size = region.vocab_start + len(region.hotcell)
    print("----------region.vocab_size is %d" % region.vocab_size)
    # build the hot cell kdtree to facilitate search
    # ?????????cell??????????????????????????????????????????????????????KD????????????????????????
    if not region.needTime:
        # ????????????cell?????????????????????????????????????????????KD???
        # todo
        coord = [cell2coord(region, cell) for cell in (region.hotcell)]
        # region.hotcell_kdtree = spatial.KDTree(coord)
        # coord = hcat(map(x->collect(cell2coord(region, x)), region.hotcell)...)
        # region.hotcell_kdtree = KDTree(coord)
        # region.built = True
    else:
        # coord = [cell2coordandtime(region, cell) for cell in (region.hotcell)]
        coord = [cell2coordandtime(region, cell) for cell in (region.hotcell)]
    region.hotcell_kdtree = spatial.KDTree(coord)
    # coord = hcat(map(x->collect(cell2coord(region, x)), region.hotcell)...)
    # region.hotcell_kdtree = KDTree(coord)
    region.built = True
    # # ????????????cell?????????????????????????????????????????????????????????????????????3????????????1,idx??? 2,idx??? 3,idx?????????idx??????cell?????????
    # #         coordandtime = hcat(map(cell->collect(cell2coordandtime(region, cell)), region.hotcell)...)
    # #         println(size(coordandtime))
    # #         n_points = size(coordandtime,2)
    # # #         dist = [rand(n_points) for _ in 1:n_points]
    # #         dist = zeros(n_points, n_points)
    # #         println(size(coordandtime))
    # #         println(Dates.format(now(), "HH:MM") )
    # #         @inbounds for i in axes(coordandtime,2)
    # #             @simd for j in (i + 1):lastindex(coordandtime,2)
    # #                 a = coordandtime[:,i]
    # #                 b = coordandtime[:,j]
    # #
    # #                 if abs2(a[1] - b[1]) + abs2(a[2] - b[2]) == 0 && abs(a[3] - b[3]) > region.nointeresttime # ??????????????????????????????
    # #                     dist[i,j] = region.maxDis + abs(a[3] - b[3])
    # #                 else
    # #                     s = sqrt(abs2(a[1] - b[1]) + abs2(a[2] - b[2]) + region.delta)
    # #                     dist[i,j]= exp(abs(a[3] - b[3]) / (region.interesttime * 6)) * s
    # #                 end
    # #             end
    # #         end
    # #         dist = dist + transpose(dist)
    # #         println(Dates.format(now(), "HH:MM") )
    # #
    # #         exit()
    # # region.hotcell_balltree = BallTree(coordandtime, DisMetric(region.interesttime, region.nointeresttime, region.delta, region.maxDis))
    # #         region.hotcell_balltree = coordandtime
    # region.built = true
    # # region.hotcell_kdtree = KDTree(coordandtime)
    # end
    return train_datas, train_labels, val_datas, val_labels, test_datas, test_labels


def lonlat2meters(lon, lat):
    semimajoraxis = 6378137.0
    east = lon * 0.017453292519943295
    north = lat * 0.017453292519943295
    t = math.sin(north)
    return semimajoraxis * east, 3189068.5 * math.log((1 + t) / (1 - t))


def coordandtime2cell(region, x, y, timestamp):
    xoffset = round(x - region.minx, 6) / region.xstep
    yoffset = round(y - region.miny, 6) / region.ystep
    # pos ???????????????????????????
    if region.timestart > timestamp:
        zoffset = (86400 - region.timestart + timestamp) // region.timestep
    else:
        zoffset = (timestamp - region.timestart) // region.timestep
    xoffset = int(math.floor(xoffset))
    yoffset = int(math.floor(yoffset))
    zoffset = int(math.floor(zoffset))
    return zoffset * (region.numx * region.numy) + yoffset * region.numx + xoffset


# def cell2coordandtime(cell, region):
def cell2coordandtime(region, cell):
    if region.use_grid:
        zoffset = cell // (region.numx * region.numy)
        cell = cell % (region.numx * region.numy)
        yoffset = cell / region.numx
        xoffset = cell % region.numx
        y = region.miny + (yoffset + 0.5) * region.ystep
        x = region.minx + (xoffset + 0.5) * region.xstep
        time = region.mintime + (zoffset + 0.5) * region.timestep
        return x, y, time
    else:
        zoffset = cell // (len(region.hulls))
        spatio_id = cell % (len(region.hulls))
        (lat, lon) = region.centers[spatio_id]
        x, y = lonlat2meters(lon, lat)
        # ?????????
        y = (y - region.miny) / (region.maxy - region.miny)
        x = (x - region.minx) / (region.maxx - region.minx)

        total_pos = 86400 // region.timestep
        angle = calAngle(zoffset, total_pos)
        # tx, ty = math.cos(math.pi * angle) / math.sqrt(2), math.sin(math.pi * angle) / math.sqrt(2)
        # tx, ty = math.cos(math.pi * angle) / 2, math.sin(math.pi * angle) / 2
        tx, ty = math.cos(math.pi * angle), math.sin(math.pi * angle)
        # tx, ty = tx * 0.1, ty * 0.1 # todo ?????? ???????????????
        # time = region.mintime + (zoffset + 0.5) * region.timestep
        return x, y, tx, ty
        # return xoffset, yoffset, zoffset


def spatioidandtime2cell(region, spatio_id, timestamp):
    # pos ???????????????????????????
    if region.timestart > timestamp:
        zoffset = (86400 - region.timestart + timestamp) // region.timestep
    else:
        zoffset = (timestamp - region.timestart) // region.timestep
    return zoffset * len(region.hulls) + spatio_id


def gpsandtime2cell(region, lon, lat, time):
    if region.use_grid:
        # to Web Mercator coordinate
        x, y = lonlat2meters(lon, lat)
        return coordandtime2cell(region, x, y, time)
    else:
        spatio_id = np.argmin(np.sum((region.centers - [lat, lon]) ** 2, 1))
        # angle = cfe(region, time) # ???????????????????????????????????????????????????????????????????????????
        return spatioidandtime2cell(region, spatio_id, time)


def knearestHotcells(region, cell, k):
    assert region.built == True
    if region.needTime:
        coordandtime = cell2coordandtime(region, cell)
        [topk_dist, topk_id] = region.hotcell_kdtree.query(coordandtime, k + 1)
    else:
        coord = cell2coord(region, cell)
        [topk_dist, topk_id] = region.hotcell_kdtree.query(coord, k + 1)
    return region.hotcell[topk_id[1:]], topk_dist[1:]

    # if cell in region.hotcell2vocab:
    #     # ????????????????????????????????????
    #     loc = region.hotcell2id[cell]
    #     idxs, dists = region.hotcell_neighbor[loc,:k], region.hotcell_neighbor_dist[loc,:k]
    # else:
    # cells_coordandtime = region.cell_coordandtime
    # x = cells_coordandtime[0][0]
    # y = cells_coordandtime[0][1]
    # z = cells_coordandtime[0][2]
    # coord = pd.concat([x, y], axis=1).to_numpy()
    # time = z.to_numpy()
    #
    # dist = np.sum((coord - coordandtime[:2]) ** 2, axis=1)
    # time = abs(coordandtime[2] - time)
    # flag1 = np.logical_and((dist == 0), (time > region.nointeresttime))
    # flag2 = np.logical_not(flag1)
    #
    # flag3 = np.logical_and(time < (region.interesttime * 0.8), flag2)
    # flag2 = np.logical_xor(flag3, flag2)
    #
    # res1 = (time + region.maxDis) * flag1
    # res2 = (np.exp(time / region.interesttime) * (dist + region.delta)) * flag2
    #
    # res3 = (dist + region.delta) * flag3
    #
    #
    # res = res1 + res2 + res3
    #
    # sort_id = np.argsort(res, kind='quicksort', order=None)
    # res = np.sort(res, kind='quicksort', order=None)
    # idxs = sort_id[:k]
    # dists = res[:k]
    return region.hotcell[idxs], dists


def nearestHotcell(region, cell):
    assert region.built == True
    hotcell, _ = knearestHotcells(region, cell, 1)
    return hotcell[0]


def cell2vocab(region, cell):
    assert region.built == True
    if cell not in region.hotcell2vocab:
        hotcell = nearestHotcell(region, cell)
        region.hotcell2vocab[cell] = region.hotcell2vocab[hotcell]
    return region.hotcell2vocab[cell]


def gpsandtime2vocab(region, lon, lat, time):
    if not inregionT(region, lon, lat, time=time):
        return UNK
    # ??????cell???????????????id
    return cell2vocab(region, gpsandtime2cell(region, lon, lat, time))


def gps2vocab(region, lon, lat):
    if not inregionS(region, lon, lat):
        return UNK
    return cell2vocab(region, gps2cell(region, lon, lat))


def tripandtime2seq(region, trj_data):
    seq = []
    for (lon, lat, time) in trj_data:
        # ???????????????????????????UNK
        seq.append(gpsandtime2vocab(region, lon, lat, time))
    # ??????seq??????????????????????????????????????????????????????????????????cell???
    items = []
    for k, _ in itertools.groupby(seq):
        items.append(str(k))
    return items


def trip2seq(region, trj_data):
    seq = []
    for (lon, lat) in trj_data:
        # ???????????????????????????UNK
        seq.append(gps2vocab(region, lon, lat))
    items = []
    for k, _ in itertools.groupby(seq):
        items.append(str(k))
    return items


def makeKneighbor(region):
    pass
    # hotcell = region.hotcell
    # hotcell2id = {}
    # for k,v in enumerate(hotcell):
    #     hotcell2id[v] = k
    # region.hotcell2id = hotcell2id
    # hotcell = pd.DataFrame(hotcell)
    # coordandtime = hotcell.apply(cell2coordandtime, args=(region,))
    # region.cell_coordandtime = coordandtime
    # x = coordandtime[0][0]
    # y = coordandtime[0][1]
    # z = coordandtime[0][2]
    # coord = pd.concat([x,y],axis=1).to_numpy()
    # time = z.to_numpy()
    # 
    # localtime = T.asctime(T.localtime(T.time()))
    # print("????????????????????? :", localtime)
    # # def distMetric(a, b):
    #     # if abs(a[0] - b[0]) ** 2 + abs(a[1] - b[1]) ** 2 == 0 and abs(
    #     #         a[2] - b[2]) > region.nointeresttime:  # ??????????????????????????????
    #     #     return region.maxDis + abs(a[2] - b[2])
    #     # else:
    #     #     s = math.sqrt(abs(a[0] - b[0]) ** 2 + abs(a[1] - b[1]) ** 2 + region.delta)
    #     #     return math.exp(abs(a[2] - b[2]) / (region.interesttime * 6)) * s
    # time = time.reshape(-1,1)
    # dist = squareform(pdist(coord, 'euclidean'))
    # time = squareform(pdist(time, 'minkowski', p=1.))
    # flag1 = np.logical_and((dist == 0), (time > region.nointeresttime))
    # flag2 = np.logical_not(flag1)
    # 
    # flag3 = np.logical_and(time < (region.interesttime * 0.8), flag2)
    # flag2 = np.logical_xor(flag3, flag2)
    # 
    # res1 = (time + region.maxDis) * flag1
    # res2 = (np.exp(time / region.interesttime) * (dist + region.delta)) * flag2
    # 
    # res3 = (dist + region.delta) * flag3
    # 
    # res = res1 + res2 + res3
    # 
    # 
    # sort_id = np.argsort(res, axis=1, kind='quicksort', order=None)
    # res = np.sort(res, axis=1, kind='quicksort', order=None)
    # neighbor = sort_id[:, :region.k]
    # region.hotcell_neighbor_dist = res[:, :region.k]
    # # neighbor = region.hotcell[neighbor]
    # localtime = T.asctime(T.localtime(T.time()))
    # print("????????????????????? :", localtime)
    # region.hotcell_neighbor = neighbor
    # region.vocab_size = len(neighbor) + region.vocab_start


def createTrainVal(region, datas, isVal, injectnoise):
    # ????????????????????????
    # trainsrc, traintrg, trainlabel = open("../data/train.src", "w"), open("../data/train.trg", "w"), open("../data/train.label", "w")
    # validsrc, validtrg, vallabel = open("../data/val.src", "w"), open("../data/val.trg", "w"), open("../data/val.label", "w")
    print("")
    print("Create *.src and *.trg files")
    srcio, trgio = (open("../data/val.src", "w"), open("../data/val.trg", "w")) if isVal else \
        (open("../data/train.src", "w"), open("../data/train.trg", "w"))

    for idx, trj_data in enumerate(datas):
        # ???????????????????????????????????????????????????????????????
        if not (region.min_length <= len(trj_data) <= region.max_length):
            continue
        # ??????????????????
        if region.needTime:
            # ??????????????????????????????????????????????????????id????????????????????????????????????cell????????????????????????cell
            trg = tripandtime2seq(region, trj_data)
            trg = " ".join(trg) + "\n"  # ???????????????????????????

            # ?????????????????????trip?????????20??????????????????????????????
            noisetrips = injectnoise(trj_data=trj_data, region=region)

            # ????????????????????????????????????????????????????????????
            # ???????????????????????????????????????????????????+?????????
            for noisetrip in noisetrips:
                ## here: feel weird
                # src = noisetrip |> trip2seq |> seq2str
                # ????????????????????????????????????????????????????????????????????????
                src = tripandtime2seq(region, noisetrip)
                src = " ".join(src) + "\n"
                srcio.write(src)
                # ??????
                trgio.write(trg)
        else:
            trg = trip2seq(region, trj_data)
            trg = " ".join(trg) + "\n"  # ???????????????????????????

            # ?????????????????????trip?????????20??????????????????????????????
            noisetrips = injectnoise(trj_data=trj_data, region=region)

            # ????????????????????????????????????????????????????????????
            for noisetrip in noisetrips:
                ## here: feel weird
                # src = noisetrip |> trip2seq |> seq2str
                src = trip2seq(region, noisetrip)
                src = " ".join(src) + "\n"
                srcio.write(src)
                # ??????
                trgio.write(trg)
            # k % 100_00 == 1 and \
        print("Writing %d %s trips ..." % (idx, "val" if isVal else "train"))

    srcio.close(), trgio.close()


def createTrainVal_OnlyOriginal(region, trj_datas, trj_labels, isVal, isTest, min_length=2, max_length=1000):
    # traintrg??????????????????????????????
    # validtrg??????????????????????????????
    # traintrg, trainlabel = open("../data/train.ori", "w"), open("../data/train.olabel", "w")
    # validtrg, vallabel = open("../data/val.ori", "w"), open("../data/val.olabel", "w")
    if isVal:
        trgio, labelio = open("../data/val.ori", "w"), open("../data/val.label", "w")
    elif isTest:
        trgio, labelio = open("../data/test.ori", "w"), open("../data/test.label", "w")
    else:
        trgio, labelio = open("../data/train.ori", "w"), open("../data/train.label", "w")

    print()
    print("Create *.ori files")
    for idx, (trj_data, trj_label) in enumerate(zip(trj_datas, trj_labels)):
        # ??????????????????
        if not (min_length <= len(trj_data) <= max_length):
            continue
        if region.needTime:
            # ??????????????????????????????????????????????????????id????????????????????????????????????cell????????????????????????cell
            trg = tripandtime2seq(region, trj_data)
        else:
            trg = trip2seq(region, trj_data)
        trg = " ".join(trg) + "\n"
        # ??????i<=???????????????????????????trgio??????traintrg???????????????validtrg
        # ??????????????????
        trgio.write(trg)
        if region.has_label:
            labelio.write(str(trj_label) + "\n")

        print("Writing %d %s trips ..." % (idx, "test" if isTest else ("val" if isVal else "train")))
    trgio.close(), labelio.close()


def saveKNearestVocabs(region):
    V = np.zeros([region.vocab_size, region.k])
    D = np.zeros([region.vocab_size, region.k])
    for vocab in range(0, region.vocab_start):
        V[vocab, :] = vocab
        D[vocab, :] = 0.0

    localtime = T.asctime(T.localtime(T.time()))
    print("????????????????????? :", localtime)
    for vocab in range(region.vocab_start, region.vocab_size):
        # ??????????????????id?????????????????????cell??????
        cell = region.vocab2hotcell[vocab]
        # ???????????????cell??????????????????????????????region????????????KD?????????knn???K??????
        kcells, dists = knearestHotcells(region, cell, region.k)
        # ???k?????????cell?????????????????????id
        kvocabs = list(map(lambda x: region.hotcell2vocab[x], kcells))
        # ??????k??????????????????k?????????V???K*vocabsize ?????????
        V[vocab, :] = kvocabs
        # ????????????
        D[vocab, :] = dists

    localtime = T.asctime(T.localtime(T.time()))
    print("????????????????????? :", localtime)
    if region.needTime:
        #     interesttime = region.interesttime
        timesize = region.timestep
        file = os.path.join("../data", region.cityname + "-vocab-dist-cell-%d.h5" % (timesize))
    else:
        cellsize = region.xstep
        file = os.path.join("../data", region.cityname + "-vocab-dist-cell%d.h5" % cellsize)
    with h5py.File(file, "w") as f:
        f["V"], f["D"] = V, D
    print("Saved cell distance into %s" % file)
