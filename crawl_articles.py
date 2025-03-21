#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import re
from datetime import datetime
import logging
import sys
from typing import List, Dict
import re

# 禁用代理设置
os.environ['no_proxy'] = '*'

class ArticleCrawler:
    def __init__(self, output_dir: str = None):
        """
        初始化文章爬虫
        :param output_dir: 文章内容保存目录，如果为None则使用默认命名
        """
        if output_dir is None:
            # 使用download_content+日期作为默认目录
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f'download_content_{current_time}'
        
        self.output_dir = output_dir
        self.logger = self._setup_logging()
        self._setup_output_dir()

    def _setup_logging(self) -> logging.Logger:
        """
        设置日志记录
        """
        os.makedirs('logs', exist_ok=True)
        log_filename = os.path.join('logs', f'article_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.INFO,  # 将日志级别从 DEBUG 改为 INFO
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def _setup_output_dir(self):
        """
        创建输出目录
        """
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f"创建输出目录: {self.output_dir}")
        except Exception as e:
            self.logger.error(f"创建输出目录失败: {str(e)}")
            raise

    def _setup_driver(self):
        """
        设置并返回Chrome驱动
        """
        try:
            self.logger.info("开始设置Chrome驱动...")
            
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            # 禁用代理设置
            options.add_argument('--proxy-server="direct://"')
            options.add_argument('--proxy-bypass-list=*')
            
            try:
                self.logger.info("正在初始化 Chrome 驱动...")
                driver = uc.Chrome(
                    options=options,
                    driver_executable_path='/Users/qinxiaoqiang//chromedriver/chromeddriver/chromedriver'
                )
                self.logger.info("Chrome驱动初始化成功")
                return driver
                
            except Exception as e:
                self.logger.error(f"Chrome驱动初始化失败: {str(e)}")
                raise
            
        except Exception as e:
            self.logger.error(f"设置Chrome驱动时出错: {str(e)}")
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        """
        # 移除非法字符
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        # 限制长度
        if len(filename) > 100:
            filename = filename[:97] + "..."
        return filename

    def _extract_article_content(self, driver) -> str:
        """
        提取文章内容并转换为Markdown格式，保留图片URL和表格内容
        """
        try:
            # 等待文章内容加载
            content_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#js_content'))
            )
            
            # 获取文章标题
            try:
                title = driver.find_element(By.CSS_SELECTOR, '#activity-name').text.strip()
            except:
                title = "无标题"

            # 构建Markdown内容
            markdown_content = f"# {title}\n\n"
            
            # 获取所有内容元素
            elements = content_element.find_elements(By.CSS_SELECTOR, 'p, section, table, img')
            
            for elem in elements:
                # 处理图片
                if elem.tag_name == 'img':
                    try:
                        img_url = elem.get_attribute('data-src')
                        if img_url:
                            alt_text = elem.get_attribute('alt') or '图片'
                            markdown_content += f"![{alt_text}]({img_url})\n\n"
                        continue
                    except:
                        continue
                
                # 处理表格
                if elem.tag_name == 'table':
                    try:
                        # 获取表格内容
                        rows = elem.find_elements(By.TAG_NAME, 'tr')
                        if not rows:
                            continue
                            
                        table_content = []
                        header_cells = rows[0].find_elements(By.TAG_NAME, 'th')
                        if not header_cells:  # 如果没有th，就用td
                            header_cells = rows[0].find_elements(By.TAG_NAME, 'td')
                            
                        # 添加表头
                        header = [cell.text.strip() for cell in header_cells]
                        table_content.append('| ' + ' | '.join(header) + ' |')
                        table_content.append('| ' + ' | '.join(['---' for _ in header]) + ' |')
                        
                        # 添加数据行
                        for row in rows[1:]:
                            cells = row.find_elements(By.TAG_NAME, 'td')
                            row_data = [cell.text.strip() for cell in cells]
                            table_content.append('| ' + ' | '.join(row_data) + ' |')
                        
                        markdown_content += '\n'.join(table_content) + '\n\n'
                        continue
                    except Exception as e:
                        self.logger.error(f"处理表格时出错: {str(e)}")
                        continue
                
                # 处理文本内容
                text = elem.text.strip()
                if not text:
                    continue
                
                # 检查段落中的图片
                images = elem.find_elements(By.TAG_NAME, 'img')
                for img in images:
                    try:
                        img_url = img.get_attribute('data-src')
                        if img_url:
                            alt_text = img.get_attribute('alt') or '图片'
                            text += f"\n![{alt_text}]({img_url})\n"
                    except:
                        continue
                
                # 添加处理后的文本
                markdown_content += f"{text}\n\n"
            
            # 删除文末广告内容
            ad_patterns = [
                r'作者：.*?编辑：.*?\n',
                r'题图：.*?\n',
                r'投稿：.*?\n',
                r'诊疗经验谈\s+\d+\s*\n',
                r'继续滑动看下一个.*?\n',
            ]
            
            for pattern in ad_patterns:
                markdown_content = re.sub(pattern, '', markdown_content, flags=re.MULTILINE|re.DOTALL)
            
            return markdown_content
            
        except Exception as e:
            self.logger.error(f"提取文章内容时出错: {str(e)}")
            return ""

    def crawl_article(self, url: str, title: str):
        """
        爬取单篇文章
        """
        driver = None
        try:
            # 准备文件名
            safe_title = self._sanitize_filename(title)
            file_path = os.path.join(self.output_dir, f"{safe_title}.md")  # 改为.md后缀
            
            # 如果文件已存在，跳过
            if os.path.exists(file_path):
                self.logger.info(f"文章已存在，跳过: {title}")
                return
            
            self.logger.info(f"开始爬取文章: {title}")
            self.logger.info(f"URL: {url}")
            
            # 设置浏览器驱动
            driver = self._setup_driver()
            
            # 访问页面
            driver.get(url)
            time.sleep(5)  # 等待页面加载
            
            # 提取文章内容
            content = self._extract_article_content(driver)
            
            if content:
                # 保存文章
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info(f"✅ 文章保存成功: {safe_title}")  # 修改日志格式，添加表情符号
            else:
                self.logger.error(f"❌ 未能提取到文章内容: {title}")  # 修改日志格式，添加表情符号
            
        except Exception as e:
            self.logger.error(f"爬取文章时出错: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def crawl_from_json(self, json_file: str):
        """
        从JSON文件读取文章列表并爬取
        """
        try:
            # 读取JSON文件
            self.logger.info(f"读取文章列表: {json_file}")
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            total = len(articles)
            self.logger.info(f"共找到 {total} 篇文章")
            
            # 遍历爬取每篇文章
            for idx, article in enumerate(articles, 1):
                self.logger.info(f"正在处理第 {idx}/{total} 篇文章")
                
                # 访问页面获取标题
                driver = self._setup_driver()
                try:
                    driver.get(article['link'])
                    time.sleep(5)  # 等待页面加载
                    
                    # 获取文章标题
                    try:
                        title = driver.find_element(By.CSS_SELECTOR, '#activity-name').text.strip()
                    except:
                        title = article.get('title', '未命名文章')  # 使用JSON中的标题作为备选
                    
                    # 爬取文章
                    self.crawl_article(article['link'], title)
                    
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                            
                time.sleep(3)  # 防止请求过于频繁
                
        except Exception as e:
            self.logger.error(f"从JSON文件爬取文章时出错: {str(e)}")
            raise

    def crawl_from_input(self):
        """
        从用户输入获取文章链接并爬取
        """
        try:
            while True:
                print("\n请输入微信文章链接（直接回车退出）：")
                url = input().strip()
                
                if not url:
                    print("程序结束")
                    break
                    
                if not url.startswith('http'):
                    print("请输入有效的URL")
                    continue
                
                # 访问页面获取标题
                driver = self._setup_driver()
                try:
                    driver.get(url)
                    time.sleep(5)  # 等待页面加载
                    
                    # 获取文章标题
                    try:
                        title = driver.find_element(By.CSS_SELECTOR, '#activity-name').text.strip()
                    except:
                        title = input("无法获取标题，请手动输入标题：").strip()
                        if not title:
                            title = "未命名文章"
                    
                    # 爬取文章
                    self.crawl_article(url, title)
                    
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                
        except Exception as e:
            self.logger.error(f"从输入爬取文章时出错: {str(e)}")
            raise

def main():
    try:
        crawler = ArticleCrawler()
        # 询问用户选择模式
        print("请选择模式：")
        print("1. 从文件批量爬取")
        print("2. 输入链接单篇爬取")
        choice = input("请输入选择（1或2）：").strip()
        
        if choice == "1":
            # 让用户选择要处理的文章列表
            print("\n请选择要处理的文章列表目录：")
            articles_dir = 'articles'
            
            # 递归查找所有包含article_list.txt或article_list.json的目录
            def find_article_lists(base_dir):
                result = []
                for root, dirs, files in os.walk(base_dir):
                    if 'article_list.txt' in files or 'article_list.json' in files:
                        # 获取相对路径
                        rel_path = os.path.relpath(root, articles_dir)
                        if rel_path != 'content':
                            result.append(rel_path)
                return result

            # 获取所有包含文章列表的目录
            subdirs = find_article_lists(articles_dir)
            
            if not subdirs:
                print("未找到任何文章列表目录")
                return
                
            # 按时间倒序排序
            subdirs.sort(reverse=True)
            
            # 显示选项
            for idx, subdir in enumerate(subdirs, 1):
                # 获取文章列表文件的信息
                full_path = os.path.join(articles_dir, subdir)
                json_file = os.path.join(full_path, 'article_list.json')
                txt_file = os.path.join(full_path, 'article_list.txt')
                
                # 检查文件存在并获取文章数量
                article_count = 0
                if os.path.exists(json_file):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            articles = json.load(f)
                            article_count = len(articles)
                    except:
                        pass
                elif os.path.exists(txt_file):
                    try:
                        with open(txt_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            article_count = sum(1 for line in lines if line.strip().startswith('链接：'))
                    except:
                        pass

                # 显示详细信息
                file_type = 'JSON' if os.path.exists(json_file) else 'TXT'
                print(f"{idx}. 目录: {subdir}")
                print(f"   文件类型: {file_type}")
                print(f"   文章数量: {article_count}")
                print()
                
            # 获取用户选择
            while True:
                try:
                    choice = int(input("\n请选择要处理的目录编号："))
                    if 1 <= choice <= len(subdirs):
                        break
                    print("无效的选择，请重试")
                except ValueError:
                    print("请输入有效的数字")
            
            # 设置选中的目录
            selected_dir = os.path.join(articles_dir, subdirs[choice-1])
            json_file = os.path.join(selected_dir, 'article_list.json')
            
            if not os.path.exists(json_file):
                print(f"文件不存在: {json_file}")
                return
                
            # 设置文章保存目录
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            content_dir = f'download_content_{current_time}'
            crawler = ArticleCrawler(content_dir)
            
            # 开始爬取
            crawler.crawl_from_json(json_file)
            
        elif choice == "2":
            print("\n请输入文章链接：")
            url = input().strip()
            
            if not url:
                print("未输入URL，程序退出")
                return
                
            if not url.startswith('http'):
                print("请输入有效的URL")
                return
                
            print("\n请输入文章标题（可选）：")
            title = input().strip()
            if not title:
                title = "未命名文章"
                
            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join('articles', f'single_{timestamp}')
            content_dir = os.path.join(output_dir, 'content')
            os.makedirs(content_dir, exist_ok=True)
            
            # 创建爬虫实例并爬取
            crawler = ArticleCrawler(content_dir)
            crawler.crawl_article(url, title)
            
        else:
            print("无效的选择")
            sys.exit(1)
            
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
