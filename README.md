2022.11.17 当前功能：读取h5文件，可视化部分轨迹（cell表示）

pipeline：
- 运行 load_data.py，读取 preprocess_conf.json 配置，不考虑时间，创建词汇表，存入 hangzhou-vocab-dist-cell.h5 中；初始化研究区域并将对象存入 /data/region.pkl
- 运行 trajectoryVIS.py，读取 region.pkl 中的研究区域对象，读取 /make_data/20200101_jianggan.h5 轨迹信息，读取 hangzhou-vocab-dist-cell.h5 词汇表信息，将轨迹转换成 cell 表示可视化轨迹。 
- [ ] 问题：可视化轨迹出现大量横向相连的边
  - 可能1：没有去噪声，细粒度画轨迹的时候，会把（可能是噪声？）画上去
  - 可能2：数据没有清洗，把非载客的轨迹段也画上去了
  - 结论：单条轨迹超出了研究区域范围，导致右侧超出范围部分跑到了左边