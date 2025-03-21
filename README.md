# 微信文章自动爬取工具

这是一个用于自动提取微信公众号文章内容的工具。支持单篇文章和文章合集的爬取，并将内容保存为Markdown格式。

## 功能特点

- 支持单篇文章和文章合集的爬取
- 自动保存为Markdown格式
- 保留文章中的图片URL和表格内容
- 自动过滤广告和无关内容
- 支持自定义输出目录
- 详细的日志记录

## 环境要求

- Python 3.7+
- Chrome浏览器
- ChromeDriver（需要与Chrome版本匹配）

## 安装步骤

1. 克隆或下载本项目

2. 安装依赖包：
```bash
pip install -r requirements.txt
```

3. 确保已安装Chrome浏览器，并下载对应版本的ChromeDriver

4. 修改ChromeDriver路径：
   打开 `auto_wx_crawler.py`，找到以下行并修改为你的ChromeDriver路径：
   ```python
   driver_executable_path='/path/to/your/chromedriver'
   ```

## 使用方法

1. 运行程序：
```bash
python auto_wx_crawler.py
```

2. 按提示输入：
   - 输出目录路径（可选，直接回车使用默认目录）
   - 要爬取的文章或合集链接

3. 等待程序完成：
   - 单篇文章：直接保存为Markdown文件
   - 文章合集：先保存文章列表，然后依次爬取每篇文章

## 输出说明

1. 目录结构：
```
download_content_YYYYMMDD_HHMMSS/
├── article_list.txt     # 文章列表（文本格式）
├── article_list.json    # 文章列表（JSON格式）
└── *.md                 # Markdown格式的文章内容
```

2. 文章内容：
   - 保留原文格式
   - 包含图片URL
   - 保留表格内容
   - 自动过滤广告

## 注意事项

1. 请确保网络连接稳定
2. 遵守微信公众平台相关规定
3. 建议适当控制爬取频率
4. 如遇到问题，查看logs目录下的日志文件

## 常见问题

1. ChromeDriver相关错误：
   - 确保Chrome浏览器已安装
   - 确保ChromeDriver版本与Chrome匹配
   - 检查ChromeDriver路径是否正确

2. 网络超时：
   - 检查网络连接
   - 适当增加等待时间
   - 减少爬取频率

3. 文章无法提取：
   - 确认链接有效性
   - 检查是否需要登录
   - 查看日志文件了解详细错误信息

## 更新日志

### v1.0.0 (2025-03-21)
- 初始版本发布
- 支持单篇文章和合集爬取
- 完整的Markdown格式转换
- 图片和表格支持
