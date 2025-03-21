#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
from datetime import datetime
import logging
import sys
from typing import List, Tuple
import os

# 禁用代理设置
os.environ['no_proxy'] = '*'

class WechatCrawler:
    def __init__(self, output_dir: str = 'articles'):
        """
        初始化爬虫
        :param output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.logger = self._setup_logging()
        self._setup_output_dir()

    def _setup_logging(self) -> logging.Logger:
        """
        设置日志记录
        """
        # 创建logs目录
        os.makedirs('logs', exist_ok=True)
        
        # 设置日志文件名（包含时间戳）
        log_filename = os.path.join('logs', f'crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        # 配置日志格式
        logging.basicConfig(
            level=logging.DEBUG,
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
            
            # 配置Chrome选项
            options = uc.ChromeOptions()
            options.add_argument('--headless')  # 无界面模式
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            try:
                # 使用 undetected_chromedriver
                self.logger.info("正在初始化 Chrome 驱动...")
                driver = uc.Chrome(
                    options=options,
                    driver_executable_path='/Users/qinxiaoqiang/chromedriver/chromeddriver/chromedriver',
                    suppress_welcome=True
                )
                self.logger.info("Chrome驱动初始化成功")
                return driver
                
            except Exception as e:
                self.logger.error(f"Chrome驱动初始化失败: {str(e)}")
                if "DevToolsActivePort file doesn't exist" in str(e):
                    self.logger.info("尝试添加额外的 Chrome 选项...")
                    options.add_argument('--remote-debugging-port=9222')
                    driver = uc.Chrome(
                        options=options,
                        driver_executable_path='/Users/qinxiaoqiang/chromedriver/chromeddriver',
                        suppress_welcome=True
                    )
                    self.logger.info("使用备用选项成功初始化Chrome驱动")
                    return driver
                raise
            
        except Exception as e:
            self.logger.error(f"设置Chrome驱动时出错: {str(e)}")
            raise

    def _scroll_and_extract(self, driver) -> List[Tuple[str, str]]:
        """
        滚动页面并提取文章信息
        """
        articles = []
        scroll_count = 0
        last_articles_count = 0
        no_new_content_count = 0
        
        try:
            while True:
                scroll_count += 1
                self.logger.debug(f"执行第 {scroll_count} 次滚动")
                
                # 滚动到底部
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(3)  # 等待内容加载
                
                # 等待文章元素出现
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li.album__list-item'))
                    )
                except Exception as e:
                    self.logger.warning(f"等待文章元素超时: {str(e)}")
                
                # 提取当前页面上的文章信息
                items = driver.find_elements(By.CSS_SELECTOR, 'li.album__list-item')
                self.logger.debug(f"当前页面找到 {len(items)} 个文章元素")
                
                for item in items:
                    try:
                        title = item.get_attribute('data-title')
                        link = item.get_attribute('data-link')
                        if title and link and (title, link) not in articles:
                            articles.append((title, link))
                            self.logger.debug(f"新增文章: {title}")
                    except Exception as e:
                        self.logger.error(f"提取文章信息时出错: {str(e)}")
                
                # 检查是否有新文章
                if len(articles) > last_articles_count:
                    self.logger.info(f"已找到 {len(articles)} 篇文章")
                    last_articles_count = len(articles)
                    no_new_content_count = 0
                else:
                    no_new_content_count += 1
                    self.logger.debug(f"连续 {no_new_content_count} 次滚动未发现新文章")
                
                # 检查是否到达底部
                if no_new_content_count >= 3:  # 连续3次未发现新内容，认为已完成
                    self.logger.info("连续多次未发现新内容，结束抓取")
                    break
                
                # 防止无限循环
                if scroll_count > 100:  # 最多滚动100次
                    self.logger.warning("达到最大滚动次数限制")
                    break
            
            return articles
            
        except Exception as e:
            self.logger.error(f"滚动和提取过程出错: {str(e)}")
            raise

    def save_articles(self, articles: List[Tuple[str, str]]):
        """
        保存文章信息到文件
        """
        try:
            # 保存为文本格式
            txt_file = os.path.join(self.output_dir, 'article_list.txt')
            self.logger.info(f"保存文本格式到: {txt_file}")
            with open(txt_file, 'w', encoding='utf-8') as f:
                for idx, (title, link) in enumerate(articles, 1):
                    f.write(f'[{idx}] 标题：{title}\n链接：{link}\n\n')
            
            # 保存为JSON格式
            json_file = os.path.join(self.output_dir, 'article_list.json')
            self.logger.info(f"保存JSON格式到: {json_file}")
            articles_json = [{'id': idx, 'title': title, 'link': link} 
                           for idx, (title, link) in enumerate(articles, 1)]
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(articles_json, f, ensure_ascii=False, indent=2)
            
            self.logger.info("文章列表保存完成")
            
        except Exception as e:
            self.logger.error(f"保存文章列表时出错: {str(e)}")
            raise

    def crawl(self, url: str):
        """
        爬取文章列表
        :param url: 微信文章合集链接
        """
        driver = None
        try:
            self.logger.info("=== 开始运行微信文章爬虫 ===")
            self.logger.info(f"目标URL: {url}")
            
            # 设置浏览器驱动
            driver = self._setup_driver()
            
            # 访问页面
            self.logger.info("正在访问页面...")
            driver.get(url)
            time.sleep(5)  # 等待页面加载
            
            # 提取文章列表
            self.logger.info("开始提取文章列表...")
            articles = self._scroll_and_extract(driver)
            self.logger.info(f"共找到 {len(articles)} 篇文章")
            
            # 保存结果
            self.save_articles(articles)
            self.logger.info("=== 爬虫运行完成 ===")
            
        except Exception as e:
            self.logger.error(f"爬虫运行出错: {str(e)}")
            raise
            
        finally:
            if driver:
                self.logger.info("关闭浏览器")
                driver.quit()

def main():
    # 微信文章合集链接
    url = "https://mp.weixin.qq.com/mp/appmsgalbum?action=getalbum&__biz=MzkxMDIzNjkzMg==&scene=1&album_id=3024152340834287618&count=3&uin=&key=&devicetype=iMac+MacBookPro18%2C1+OSX+OSX+14.5+build(23F79)&version=13080a10&lang=zh_CN&nettype=WIFI&ascene=0&fontScale=100"
    
    try:
        crawler = WechatCrawler()
        crawler.crawl(url)
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
