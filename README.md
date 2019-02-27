# [python3-concurrency-mzitu](http://www.madmalls.com/blog/post/python3-concurrency-pics-02/)

[![Python](https://img.shields.io/badge/python-v3.4%2B-blue.svg)](https://www.python.org/)
[![aiohttp](https://img.shields.io/badge/aiohttp-v3.3.2-brightgreen.svg)](https://aiohttp.readthedocs.io/en/stable/)
[![BeautifulSoup4](https://img.shields.io/badge/BeautifulSoup4-v4.6.3-orange.svg)](https://pypi.org/project/beautifulsoup4/)
[![requests](https://img.shields.io/badge/requests-v2.19.1-yellow.svg)](http://docs.python-requests.org/en/master/)
[![pymongo](https://img.shields.io/badge/pymongo-v3.7.1-red.svg)](https://pypi.org/project/pymongo/)
[![progressbar2](https://img.shields.io/badge/progressbar2-v3.38.0-lightgrey.svg)](https://pypi.org/project/progressbar2/)

# 1. 进度条

![](http://www.madmalls.com/api/medias/uploaded/async-mzitu-02-75e2c01f.png)


# 2. 部分截图

![](http://www.madmalls.com/api/medias/uploaded/mzitu-01-e91219db.png)
![](http://www.madmalls.com/api/medias/uploaded/mzitu-02-bacf231f.png)

> 分析爬取的过程：

![](http://www.madmalls.com/api/medias/uploaded/mzitu-022a41aa.jpg)


# 3. 使用方法

## 3.1 下载代码

```bash
[root@CentOS ~]# git clone https://github.com/wangy8961/python3-concurrency-pics-02.git
[root@CentOS ~]# cd python3-concurrency-pics-02/
```

## 3.2 准备虚拟环境

如果你的操作系统是`Linux`:

```bash
[root@CentOS python3-concurrency-pics-02]# python3 -m venv venv3
[root@CentOS python3-concurrency-pics-02]# source venv3/bin/activate
```

> `Windows`激活虚拟环境的命令是: `venv3\Scripts\activate`

## 3.3 安装依赖包

如果你的操作系统是`Linux`:

```bash
(venv3) [root@CentOS python3-concurrency-pics-02]# pip install -r requirements-linux.txt
```

如果你的操作系统是`Windows`（不会使用`uvloop`）:

```bash
(venv3) C:\Users\wangy> pip install -r requirements-win32.txt
```

## 3.4 测试

由于图片有13万多张，所以测试的时候，你可以指定只下载100个图集来对比`同步下载`、`多线程下载`和`异步下载`的效率区别，**修改以下三个脚本中的`TEST_NUM = 100`**

建议每次测试完，都删除相关目录：

```bash
(venv3) [root@CentOS python3-concurrency-pics-02]# rm -rf downloads/ logs/ __pycache__/
```

删除数据库记录：

```bash
(venv3) [root@CentOS python3-concurrency-pics-02]# mongo
MongoDB shell version v3.6.6
connecting to: mongodb://127.0.0.1:27017
...
> show dbs
admin   0.000GB
config  0.000GB
local   0.000GB
mzitu   0.036GB
> use mzitu
switched to db mzitu
> db.dropDatabase()
{ "dropped" : "mzitu", "ok" : 1 }
> show dbs
admin   0.000GB
config  0.000GB
local   0.000GB
> 
```

### (1) 依序下载

```python
(venv3) [root@CentOS python3-concurrency-pics-02]# python sequential.py
```

### (2) 多线程下载

```python
(venv3) [root@CentOS python3-concurrency-pics-02]# python threadpool.py
```

### (3) 异步下载

```python
(venv3) [root@CentOS python3-concurrency-pics-02]# python asynchronous.py
```

# 4. 爬虫系列

## 4.1 理论

- [Python3爬虫系列01 (理论) - I/O Models 阻塞 非阻塞 同步 异步](http://www.madmalls.com/blog/post/io-models/)
- [Python3爬虫系列02 (理论) - Python并发编程](http://www.madmalls.com/blog/post/concurrent-programming-for-python/)
- [Python3爬虫系列06 (理论) - 可迭代对象、迭代器、生成器](http://www.madmalls.com/blog/post/iterable-iterator-and-generator-in-python/)
- [Python3爬虫系列07 (理论) - 协程](http://www.madmalls.com/blog/post/coroutine-in-python/)
- [Python3爬虫系列08 (理论) - 使用asyncio模块实现并发](http://www.madmalls.com/blog/post/asyncio-howto-in-python3/)


## 4.2 实验

- [Python3爬虫系列03 (实验) - 同步阻塞下载](http://www.madmalls.com/blog/post/sequential-download-for-python/)
- [Python3爬虫系列04 (实验) - 多进程并发下载](http://www.madmalls.com/blog/post/multi-process-for-python3/)
- [Python3爬虫系列05 (实验) - 多线程并发下载](http://www.madmalls.com/blog/post/multi-thread-for-python/)
- [Python3爬虫系列09 (实验) - 使用asyncio+aiohttp并发下载](http://www.madmalls.com/blog/post/aiohttp-howto-in-python3/)


## 4.3 实战

- [Python3爬虫系列10 (实战) - 爬取妹子图 第一弹](http://www.madmalls.com/blog/post/python3-concurrency-pics-01/)
- [Python3爬虫系列11 (实战) - 爬取妹子图 第二弹](http://www.madmalls.com/blog/post/python3-concurrency-pics-02/)