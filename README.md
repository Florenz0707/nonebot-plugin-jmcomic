# NONEBOT-PLUGIN-JMCOMIC

## 前言
因为不知道怎么用`localstore`重定向配置文件的路径所以没有发表该插件

有功能需求的同学可以看看。

## 使用说明
1. `git clone https://github.com/Florenz0707/nonebot-plugin-jmcomic.git` 到你的项目根目录下。
2. 在`pyproject.toml`的`plugins_dir`中添加`"nonebot_plugin_jmcomic"`。
3. 打开`src`目录下的`PathRelocator.py`。
4. 将`_base_dir`修改为`nonebot_plugin_jmcomic`的绝对路径。
5. 将`_login_user_name`修改为你的jm用户名。
6. 将`_login_pwd`修改为你的jm登录密码。
7. 将`_proxy_host`修改为你的代理地址。
8. 将`_cookies_AVS`修改为你的cookies_AVS（详情请查看[JMCOMIC-Crawler-Python：配置文件指南](https://github.com/hect0x7/JMComic-Crawler-Python/blob/master/assets/docs/sources/option_file_syntax.md)）
9. 相关依赖请自行下载。

## 项目目录结构
```
nonebot_plugin_jmcomic
    - config
        - default_options.yml       # 默认下载配置文件
        - firstImage_options.yml    # 用于过滤首图的配置文件
        - proxyClient.yml           # 使用代理以访问html端的配置文件
    - data
        - album_cache   # 下载本子时的缓存文件夹，每次下载完毕自动删除文件
        - save_cache    # 下载缓存，超过容量自动删除
            - pdf       # PDF
            - pics      # 首图
        - database      # 数据库
    - src   # 源代码
```

## 项目特色功能
### 存储机制
1. 对本子下载产生的中间文件进行及时清除以节省资源。 
2. 设置数据库以记录查询过的本子信息，设置下载缓存以防止大量的重复下载（采用FIFO），节省资源和时间。

### 下载保护
1. 限制下载队列长度。 
2. 设置用户每日使用上限，查询和下载均计入次数。 
3. 设置标签与本子id黑名单检查。

### XP记录
依据用户的下载记录，统计标签，得出用户xp。

## 命令列表
1. `jm.d <id> [-f]` 下载本子号为`id`的本子。使用`-f`选项可无视黑名单强行下载（仅限SUPERUSER）。
2. `jm.q <id> [-i]` 查询本子号为`id`的本子。信息包括标题、作者、标签、预计大小（若已经下载过），使用`-i`选项可以附带首图。
3. `jm.r [-q]` 随机生成可用的本子号。使用`-q`选项可以直接附带首图查询。
4. `jm.xp [-u qq] [-l len]` 查询用户xp。使用`-u`选项指定查询用户，默认查询自身。使用`-l`选项指定展示长度，默认为5。
5. `jm.m` SUPERUSER使用的管理命令，具体如下：
6. `cache` 查看当前缓存使用情况。
7. `proxy` 开启/关闭代理。
8. `f_s` 查看今日用户使用情况（仅统计下载与查询）。
9. `(d/u)_(s/c)` 显示或清空当前下载或上传队列。
10. `(r/l)_(s/i/d)` 对本子黑名单或用户使用限制进行管理，具体参数请看源码。