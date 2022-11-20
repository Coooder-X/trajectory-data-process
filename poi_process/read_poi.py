import pandas as pd
import os
import matplotlib.pyplot as plt
from scipy import spatial


# import POI


# ['名称', '大类', '中类', '小类', '地址', '省', '市', '区', 'WGS84_经度', 'WGS84_纬度']


def getPOI_Coor(data_dir, file_name):
    print(os.listdir(data_dir))
    print('当前文件: ', file_name)
    file_list = os.listdir('../../hangzhou-POI')
    for i in range(len(file_list)):
        file_list[i] = data_dir + '/' + file_list[i]
        print(file_list[i])

    df1 = pd.read_excel(data_dir + '/' + file_name)  # 读取xlsx中的第一个sheet
    poi_coor = df1.iloc[:, [-2, -1]].values
    print(poi_coor)
    return poi_coor


"""
将所有POI坐标放入 KDTree，方便查找邻近点，从距离上判断连通性
:param: GPS 经纬度格式的POI数组
:return 存储POI坐标的 KDTree
"""
def buildKDTree(pois):
    kdtree = spatial.KDTree(pois)
    return kdtree


"""
将轨迹的头尾节点坐标放入 points，分别查找邻近点，从距离上判断连通性，返回通过轨迹头尾节点过滤后的poi数组
:param: trips：经纬度格式的轨迹数组，poi_coor：所有经纬度表示的POI节点，存储所有轨迹头尾节点经纬度坐标的 KDTree、最邻近的点数 k
:return coor_filtered：[[经度, 纬度], [lon, lat], ...] 形状的经过过滤的坐标数组
"""
def getPOI_CoorFiltered(trips, poi_coor, kdtree, k):
    points = []
    for trip in trips:
        points.append([trip[0][0], trip[0][1]])
        points.append([trip[-1][0], trip[-1][1]])
    topk_dist, topk_id = kdtree.query(points, k)
    coor_filtered = []
    for row in topk_id:
        if k == 1:
            coor_filtered.append(poi_coor[row])
        else:
            for id in row:
                coor_filtered.append(poi_coor[id])
    return coor_filtered


def showPOI_Coor(poi_coor):
    fig = plt.figure(figsize=(20, 10))
    ax = fig.subplots()

    ax.scatter(poi_coor[:, 0], poi_coor[:, 1], c='g', marker='o')
    ax.set_xlabel('lon')  # 画出坐标轴
    ax.set_ylabel('lat')
    plt.show()


if __name__ == "__main__":
    data_dir = '../../hangzhou-POI'
    file_name = '商务住宅.xlsx'

    showPOI_Coor(getPOI_Coor(data_dir, file_name))

# data_dir = '../../hangzhou-POI'
# print(os.listdir(data_dir))
# file_list = os.listdir('../../hangzhou-POI')
# for i in range(len(file_list)):
#     file_list[i] = data_dir + '/' + file_list[i]
#     print(file_list[i])
#
# # ['名称', '大类', '中类', '小类', '地址', '省', '市', '区', 'WGS84_经度', 'WGS84_纬度']
# df1 = pd.read_excel('../../hangzhou-POI/商务住宅.xlsx')  # 读取xlsx中的第一个sheet
# # print('当前文件: ', file_list[4])
# data1 = df1.head(10)  # 读取前10行所有数据
# # data2 = df1.values  # list【】  相当于一个矩阵，以行为单位
# # print(df1.keys())
#
# poi_coor = df1.iloc[:, [-2, -1]].values
# print(poi_coor)
# min_longitude = min(poi_coor[:, 0])
# min_latitude = min(poi_coor[:, 1])
# max_longitude = max(poi_coor[:, 0])
# max_latitude = max(poi_coor[:, 1])
#
# fig = plt.figure(figsize=(20, 10))
# ax = fig.subplots()
#
# ax.scatter(poi_coor[:, 0], poi_coor[:, 1], c='g', marker='o')
# ax.set_xlabel('lon')  # 画出坐标轴
# ax.set_ylabel('lat')
# plt.show()
