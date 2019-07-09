###
# 这是同步下载的版本，速度非常慢，想要协程高速版本的话，请访问:
# https://madmalls.com/blog/post/python3-concurrency-pics-02/
###
from datetime import datetime
import os
import re
import time
from bs4 import BeautifulSoup
import progressbar
import pymongo
import requests
from logger import logger


# 默认值0，下载MongoDB中所有的图集。如果你只要测试下载10个图集，则修改此值为10
TEST_NUM = 0
# 默认值False，只下载MongoDB中未访问过的图片URL。如果你删除了磁盘上部分图片，想补全，则设置为True
RE_DOWN = False

# 连接MongoDB
client = pymongo.MongoClient(host='localhost', port=27017)
db = client.mzitu  # 数据库名
collection_albums = db.albums  # 图集
collection_albums.create_index('album_url', unique=True)

collection_image_pages = db.image_pages  # 包含图片的页面
collection_image_pages.create_index('image_page_url', unique=True)

collection_images = db.images   # 图片资源
collection_images.create_index('image_url', unique=True)

# 设置图片下载后的保存基目录
basepath = os.path.abspath(os.path.dirname(__file__))  # 当前模块文件的根目录
download_path = os.path.join(basepath, 'downloads')
if not os.path.exists(download_path):
    os.mkdir(download_path)
    logger.critical('Create base directory [{}]'.format(download_path))


def get_response(url, info='image url', *args, **kwargs):
    '''捕获request.get()方法的异常，比如连接超时、被拒绝等
    如果请求成功，则返回响应体；如果请求失败，则返回None，所以在调用get_response()函数时需要先判断返回值
    '''
    s = requests.session()
    s.keep_alive = False

    try:
        resp = requests.get(url, *args, **kwargs)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        # In the event of the rare invalid HTTP response, Requests will raise an HTTPError exception (e.g. 401 Unauthorized)
        logger.error('Unsuccessfully get {} [{}], HTTP Error: {}'.format(info, url, errh))
        pass
    except requests.exceptions.ConnectionError as errc:
        # In the event of a network problem (e.g. DNS failure, refused connection, etc)
        logger.error('Unsuccessfully get {} [{}], Connecting Error: {}'.format(info, url, errc))
        pass
    except requests.exceptions.Timeout as errt:
        # If a request times out, a Timeout exception is raised. Maybe set up for a retry, or continue in a retry loop
        logger.error('Unsuccessfully get {} [{}], Timeout Error: {}'.format(info, url, errt))
        pass
    except requests.exceptions.TooManyRedirects as errr:
        # If a request exceeds the configured number of maximum redirections, a TooManyRedirects exception is raised. Tell the user their URL was bad and try a different one
        logger.error('Unsuccessfully get {} [{}], Redirect Error: {}'.format(info, url, errr))
        pass
    except requests.exceptions.RequestException as err:
        # catastrophic error. bail.
        logger.error('Unsuccessfully get {} [{}], Else Error: {}'.format(info, url, err))
        pass
    except Exception as err:
        logger.error('Unsuccessfully get {} [{}], Exception: {}'.format(info, url, err.__class__))
        pass
    else:
        return resp


def get_albums(url):
    '''请求入口页面，BeautifulSoup解析返回的HTTP响应，从中获取所有图集的URL
    :return:
        find_albums: 本次请求入口页面后，一共找到多个图集
        new_albums: 有多少个是新增的（即数据库之前没有记录的）
    '''
    find_albums = 0  # 一共找到多个图集
    new_albums = 0  # 有多少个是新增的（即数据库之前没有记录的）

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
    }
    # 返回入口页面的HTTP响应
    # TODO: 捕获request.get方法的异常，比如连接超时、被拒绝等
    resp = get_response(url, info='start url', headers=headers)
    if not resp:  # 请求失败时，resp为None，不能往下执行
        logger.error('Exception {} on URL [{}]'.format(e.__class__, url))
        return
    # 使用lxml解析器，解析返回的响应（HTML文档）
    soup = BeautifulSoup(resp.text, 'lxml')
    # 每个图集按年份/月份被放在 <div class='all'></div> 下面的每个<a href="图集URL">图集标题<a> 中
    try:
        a_tags = soup.find('div', {'class': 'all'}).find_all('a')  # <class 'bs4.element.ResultSet'>
    except Exception as e:
        logger.error('Exception {} on URL [{}]'.format(e.__class__, url))
        return
    logger.critical('URL [{}] has [{}] <a></a> tags'.format(url, len(a_tags)))

    for a in a_tags:
        # 判断每个<a></a>标签中的URL是不是符合图集URL格式，如果不是，则递归调用它看看它下面有没有相同URL
        # 因为有一个 https://www.mzitu.com/old/

        # 在 https://www.mzitu.com/old/ 页面中第一个URL 又是 https://www.mzitu.com/all/ 需要排除它，不然就无限死循环了
        if a['href'] == 'https://www.mzitu.com/all/':
            continue

        if re.match(r'https://www.mzitu.com/\d+', a['href']):
            data = {
                'album_title': a.get_text(),  # 每个图集的标题
                'album_url': a['href'],  # 每个图集的URL
                'created_at': datetime.utcnow(),  # 何时添加到MongoDB的
                'visited': 0  # 表明此图集URL没被访问过
            }
            if TEST_NUM and TEST_NUM == collection_albums.count_documents({}):  # 如果是测试，MongoDB中永远只能存在 TEST_NUM 个集合
                find_albums += 1  # 增加找到的图集计数
                continue
            else:
                if not collection_albums.find_one({'album_url': data['album_url']}):  # 如果是新图集，保存到MongoDB
                    new_albums += 1  # 增加新图集计数
                    collection_albums.insert_one(data)
                    logger.debug('Successfully saved album {} [{}] to MongoDB'.format(data['album_title'], data['album_url']))
                find_albums += 1  # 增加找到的图集计数
        else:  # 此<a></a>标签包含的URL不是一个合法的图集地址，即将递归获取它下面的图集
            logger.critical('Tag [<a href="{}">{}</a>] is invalid, recursive call this function'.format(a['href'], a.get_text()))
            recursive_find_albums, recursive_new_albums = get_albums(a['href'])
            find_albums += recursive_find_albums
            new_albums += recursive_new_albums

    return find_albums, new_albums


def get_image_pages(album):
    '''请求图集页面，BeautifulSoup解析返回的HTTP响应，从中获取此图集下所有图片页面（非真正图片资源）'''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
    }
    # 返回一个图集页面的HTTP响应
    # TODO: 捕获request.get方法的异常，比如连接超时、被拒绝等
    resp = get_response(album['album_url'], info='album url', headers=headers)
    if not resp:  # 请求失败时，resp为None，不能往下执行
        return {
            'failed': True  # 用于告知get_image_pages()的调用方，请求此图集URL时失败了
        }
    # 使用lxml解析器，解析返回的响应（HTML文档）
    soup = BeautifulSoup(resp.text, 'lxml')
    # 图集发布日期，后续保存时要按年份/月份创建目录
    try:
        date_span = soup.find('div', {'class': 'main-meta'}).find_all('span')[1].get_text()  # 类似于'发布于 2014-06-20 13:09'
    except Exception as e:
        logger.error('Exception {} on URL [{}]'.format(e.__class__, album['album_url']))
        return {
            'failed': True  # 用于告知get_image_pages()的调用方，请求此图集URL时失败了
        }
    published_at = re.search(r'\d+-\d+', date_span).group()  # 类似于2014-06
    # 图集有多少张图片
    try:
        images_num = int(soup.find('div', {'class': 'pagenavi'}).find_all('span')[-2].get_text())
    except Exception as e:
        logger.error('Exception {} on URL [{}]'.format(e.__class__, album['album_url']))
        return {
            'failed': True  # 用于告知get_image_pages()的调用方，请求此图集URL时失败了
        }
    logger.debug('Album {} [{}] has [{}] images'.format(album['album_title'], album['album_url'], images_num))

    # 按日期创建目录
    date_path = os.path.join(download_path, published_at)
    if not os.path.exists(date_path):
        os.mkdir(date_path)
        logger.debug('Create date directory [{}]'.format(date_path))

    # 为每个图集创建一个目录
    album_name = '[{}P] '.format(images_num) + re.sub('[\/:*?"<>|]', '_', album['album_title'])  # 注意要去除标题的非法字符
    album_path = os.path.join(date_path, album_name)
    if not os.path.exists(album_path):
        os.mkdir(album_path)
        logger.debug('Create album directory [{}]'.format(album_path))

    # 构建图集下所有包含真实图片资源的页面URL
    for i in range(1, images_num + 1):
        data = {
            'image_page_url': album['album_url'] + '/' + str(i),  # 每张图片的所在页面的URL，还不是图片的真实地址
            'image_idx': i,  # 每张图片的所在页面在图集中的序号
            'album_url': album['album_url'],  # 所属图集的URL
            'album_title': album['album_title'],  # 所属图集的标题
            'album_path': os.path.join(published_at, album_name),  # 所属图集的相对路径，不使用绝对路径是因为可能会移动此脚本
            'created_at': datetime.utcnow(),  # 何时添加到MongoDB的
            'visited': 0  # 表明此图片页面URL没被访问过
        }
        # 保存到MongoDB
        if not collection_image_pages.find_one({'image_page_url': data['image_page_url']}):
            collection_image_pages.insert_one(data)
            logger.debug('Successfully saved image page No.{} [{}] of album {} [{}] to MongoDB'.format(data['image_idx'], data['image_page_url'], data['album_title'], data['album_url']))

    # 更新图集的collection，增加字段
    data = {
        'album_published_at': re.search('\s(.*)', date_span).group(1),  # 图集的发布时间
        'album_images_num': images_num,  # 图集的图片数
        'album_path': os.path.join(published_at, album_name),  # 图集的保存路径，不使用绝对路径是因为可能会移动此脚本
        'visited': 1,  # 表明此图集URL被访问过，下次不用再访问它来获取此图集下的图片页面
        'visited_at': datetime.utcnow()  # 何时被访问过
    }
    collection_albums.update_one({'album_url': album['album_url']}, {'$set': data})

    return {
        'failed': False  # 用于告知get_image_pages()的调用方，此图集被正常访问
    }


def get_image(image_page):
    '''请求包含图片资源链接的图片页面，BeautifulSoup解析返回的HTTP响应，从中获取真正的图片资源URL'''
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
    }
    # 返回一个图片所在页面的HTTP响应
    # TODO: 捕获request.get方法的异常，比如连接超时、被拒绝等
    resp = get_response(image_page['image_page_url'], info='image page url', headers=headers)
    if not resp:  # 请求失败时，resp为None，不能往下执行
        return {
            'failed': True  # 用于告知get_image()的调用方，请求此图片页面URL时失败了
        }
    # 使用lxml解析器，解析返回的响应（HTML文档）
    soup = BeautifulSoup(resp.text, 'lxml')
    # 获取图片的真实地址
    try:
        image_url = soup.find('div', {'class': 'main-image'}).find('img')['src']
    except Exception as e:  # 偶尔有一些图集中间某几个图片页面会返回响应，但响应中没有main-image，即找不到有效的图片资源URL，比如https://www.mzitu.com/57773/41
        logger.error('Image page No.{} [{}] of album {} [{}] has no valid image URL'.format(image_page['image_idx'], image_page['image_page_url'], image_page['album_title'], image_page['album_url']))
        # 更新图片页面的collection，增加字段
        data = {
            'visited': 1,  # 表明此图片页面URL被访问过，下次不用再访问它来获取它对应的真实图片资源的URL
            'visited_at': datetime.utcnow()  # 何时被访问过
        }
        collection_image_pages.update_one({'image_page_url': image_page['image_page_url']}, {'$set': data})
        return {
            'failed': True  # 用于告知get_image()的调用方，请求此图片页面URL时失败了
        }
    # 还有一些image_url的值不是有效的图片链接，比如https://www.mzitu.com/57773/40获得的image_url就是'https:\n</p>\n</div>\r\n            <div class='
    if not re.match(r'https://.*?\.(jpe|jpg|jpeg|png|gif)', image_url):  # https://www.mzitu.com/23077/18图片页面返回的是https://i.meizitu.net/2014/03/20140315qc18.jpe
        logger.error('Image page No.{} [{}] of album {} [{}] has no valid image URL'.format(image_page['image_idx'], image_page['image_page_url'], image_page['album_title'], image_page['album_url']))
        # 更新图片页面的collection，增加字段
        data = {
            'visited': 1,  # 表明此图片页面URL被访问过，下次不用再访问它来获取它对应的真实图片资源的URL
            'visited_at': datetime.utcnow()  # 何时被访问过
        }
        collection_image_pages.update_one({'image_page_url': image_page['image_page_url']}, {'$set': data})
        return {
            'failed': True  # 用于告知get_image()的调用方，请求此图片页面URL时失败了
        }

    # 准备用这个名称来保存图片
    image_name = image_url.split('/')[-1]
    # 图片保存的相对路径，不使用绝对路径是因为可能会移动此脚本
    image_path = os.path.join(image_page['album_path'], image_name)

    data = {
        'image_url': image_url,
        'image_path': image_path,
        'image_idx': image_page['image_idx'],  # 每张图片在图集中的序号
        'album_url': image_page['album_url'],  # 所属图集的URL
        'album_title': image_page['album_title'],  # 所属图集的标题
        'created_at': datetime.utcnow(),  # 何时添加到MongoDB的
        'visited': 0  # 表明此图片资源URL没被访问过
    }
    # 保存到MongoDB
    if not collection_images.find_one({'image_url': data['image_url']}):
        collection_images.insert_one(data)
        logger.debug('Successfully saved image No.{} [{}] of album {} [{}] to MongoDB'.format(data['image_idx'], data['image_url'], data['album_title'], data['album_url']))

    # 更新图片页面的collection，增加字段
    data = {
        'visited': 1,  # 表明此图片页面URL被访问过，下次不用再访问它来获取它对应的真实图片资源的URL
        'visited_at': datetime.utcnow()  # 何时被访问过
    }
    collection_image_pages.update_one({'image_page_url': image_page['image_page_url']}, {'$set': data})

    return {
        'failed': False  # 用于告知get_image()的调用方，此图片页面被正常访问
    }


def download_image(image):
    '''请求真正的图片资源URL，下载图片到本地'''
    # 如果是因为删除了磁盘上的部分图片，补全时要设置RE_DOWN=True。但是该图片可能之前没被删除，如果图片已存在，则不重复下载
    if os.path.exists(os.path.join(download_path, image['image_path'])):
        logger.debug('No.{} image [{}] of ablum [{}] already exist, ignore download'.format(image['image_idx'], image['image_url'], image['album_url']))
        return {
            'ignored': True  # 用于告知download_image()的调用方，此图片被忽略下载
        }

    # 下载图片: mzitu.com设置了防盗链，要访问图片资源，必须在请求头中指定此图片所属相册的URL，比如Referer: https://www.mzitu.com/138611
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36',
        'Referer': image['album_url']
    }
    # TODO: 捕获request.get方法的异常，比如连接超时、被拒绝等
    resp = get_response(image['image_url'], info='image url', headers=headers)
    if not resp:  # 请求失败时，resp为None，不能往下执行
        return {
            'failed': True  # 用于告知download_image()的调用方，请求此图片URL时失败了
        }

    # 如果是补全被删除的图片，则要先创建图集的目录
    album_path = os.path.join(download_path, os.path.split(image['image_path'])[0])
    if not os.path.exists(album_path):
        os.makedirs(album_path)  # 递归创建目录
        logger.debug('Create album directory [{}]'.format(album_path))
    # 保存图片到本地
    with open(os.path.join(download_path, image['image_path']), 'wb') as f:
        f.write(resp.content)
    logger.debug('No.{} image [{}] of ablum {} [{}] download complete'.format(image['image_idx'], image['image_url'], image['album_title'], image['album_url']))

    # 更新图片资源的collection，增加字段
    data = {
        'visited': 1,  # 表明此图片资源URL被访问过，只能说明这张图片曾经被下载过，但可能人为将它从本地目录中删除，所以还是需要运行此函数，通过判断图片存不存在再决定是否下载
        'visited_at': datetime.utcnow()  # 何时被访问过，即最近一次被下载的时间
    }
    collection_images.update_one({'image_url': image['image_url']}, {'$set': data})

    return {
        'failed': False  # 用于告知download_image()的调用方，此图片被成功下载
    }


def step01():
    t1 = time.time()
    # 入口页面
    start_url = 'https://www.mzitu.com/all/'
    # 访问入口页面，将所有图集信息保存到MongoDB
    result = get_albums(start_url)
    if not result:  # 如果访问入口页面失败，则结束整个应用
        return
    else:
        logger.critical('Find [{}] albums, insert [{}] new albums into MongoDB'.format(result[0], result[1]))
        logger.critical('Step 01 cost {:.2f} seconds'.format(time.time() - t1))


def step02():
    t2 = time.time()
    ignored_ablums = collection_albums.count_documents({'visited': 1})  # 被忽略的图集数
    visited_ablums = 0  # 请求成功的图集数
    failed_ablums = 0  # 请求失败的图集数
    albums = collection_albums.find({'visited': 0})  # 所有未访问过的图集

    with progressbar.ProgressBar(max_value=collection_albums.count_documents({'visited': 0})) as bar:
        for i, album in enumerate(albums):
            result = get_image_pages(album)
            if result.get('failed'):
                failed_ablums += 1
            else:
                visited_ablums += 1
            bar.update(i)

    logger.critical('Ignored [{}] albums, visited [{}] albums, failed [{}] albums'.format(ignored_ablums, visited_ablums, failed_ablums))
    logger.critical('Step 02 cost {:.2f} seconds'.format(time.time() - t2))


def step03():
    t3 = time.time()
    ignored_image_pages = collection_image_pages.count_documents({'visited': 1})  # 被忽略的图片页面数
    visited_image_pages = 0  # 请求成功的图片页面数
    failed_image_pages = 0  # 请求失败的图片页面数
    image_pages = collection_image_pages.find({'visited': 0})  # 所有未访问过的图片页面

    with progressbar.ProgressBar(max_value=collection_image_pages.count_documents({'visited': 0})) as bar:
        for i, image_page in enumerate(image_pages):
            result = get_image(image_page)
            if result.get('failed'):
                failed_image_pages += 1
            else:
                visited_image_pages += 1
            bar.update(i)

    logger.critical('Ignored [{}] image pages, visited [{}] image pages, failed [{}] image pages'.format(ignored_image_pages, visited_image_pages, failed_image_pages))
    logger.critical('Step 03 cost {:.2f} seconds'.format(time.time() - t3))


def step04():
    t4 = time.time()
    visited_images = 0  # 请求成功的图片数
    failed_images = 0  # 请求失败的图片数

    if RE_DOWN:
        ignored_images = 0  # 被忽略的图片数
        images = collection_images.find()
        max_value = collection_images.count_documents({})
    else:
        ignored_images = collection_images.count_documents({'visited': 1})  # 被忽略的图片数
        images = collection_images.find({'visited': 0})  # 所有未访问过的图片URL
        max_value = collection_images.count_documents({'visited': 0})

    with progressbar.ProgressBar(max_value=max_value) as bar:
        for i, image in enumerate(images):
            result = download_image(image)
            if result.get('ignored'):
                ignored_images += 1
            else:
                if result.get('failed'):
                    failed_images += 1
                else:
                    visited_images += 1
            bar.update(i)

    logger.critical('Ignored [{}] images, visited [{}] images, failed [{}] images'.format(ignored_images, visited_images, failed_images))
    logger.critical('Step 04 cost {:.2f} seconds'.format(time.time() - t4))


if __name__ == '__main__':
    t0 = time.time()
    # Step 01: 访问入口页面，将所有图集信息保存到MongoDB
    step01()
    # Step 02: 从MongoDB获取所有图集页面，获取每个图集下面的所有包含真实图片资源的页面URL
    step02()
    # Step 03: 从MongoDB获取图片页面，获取真实图片资源的URL
    step03()
    # Step 04: 从MongoDB获取真实图片资源的URL，下载到本地
    step04()
    logger.critical('Total Cost {:.2f} seconds'.format(time.time() - t0))
