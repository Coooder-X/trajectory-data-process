2022.11.17 当前功能：读取h5文件，可视化部分轨迹（cell表示）

pipeline：
- 运行 load_data.py，读取 preprocess_conf.json 配置，不考虑时间，创建词汇表，存入 hangzhou-vocab-dist-cell.h5 中；初始化研究区域并将对象存入 /data/region.pkl
- 运行 trajectoryVIS.py，读取 region.pkl 中的研究区域对象，读取 /make_data/20200101_jianggan.h5 轨迹信息，读取 hangzhou-vocab-dist-cell.h5 词汇表信息，将轨迹转换成 cell 表示可视化轨迹。 