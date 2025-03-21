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
import urllib.parse

# 禁用代理设置
os.environ['no_proxy'] = '*'

class AutoWxCrawler:
    """
    微信文章自动爬取工具
    整合了文章列表提取和文章内容爬取功能
    """
    def __init__(self, output_dir: str = None):
        """
        初始化爬虫
        :param output_dir: 输出目录，如果为None则使用默认命名（download_content+日期）
        """
        if output_dir is None:
            # 使用download_content+日期作为默认目录
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f'download_content_{current_time}'
        
        self.output_dir = output_dir
        self.logger = self._setup_logging()
        self._setup_output_dir()

    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        os.makedirs('logs', exist_ok=True)
        log_filename = os.path.join('logs', f'auto_crawler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def _setup_output_dir(self):
        """创建输出目录"""
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"输出目录: {self.output_dir}")

    def _setup_driver(self):
        """设置并返回Chrome驱动"""
        try:
            self.logger.info("开始设置Chrome驱动...")
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            driver = uc.Chrome(
                options=options,
                driver_executable_path='/Users/qinxiaoqiang/chromedriver/chromeddriver/chromedriver',
                suppress_welcome=True
            )
            self.logger.info("Chrome驱动初始化成功")
            return driver
        except Exception as e:
            self.logger.error(f"设置Chrome驱动时出错: {str(e)}")
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 替换Windows和Unix系统中的非法字符
        illegal_chars = r'[<>:"/\\|?*\n\r\t]'
        filename = re.sub(illegal_chars, '_', filename)
        # 限制文件名长度
        if len(filename) > 200:
            filename = filename[:197] + '...'
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

            # 获取文章来源
            try:
                source = driver.find_element(By.CSS_SELECTOR, '#js_name').text.strip()
            except:
                source = ""

            # 构建Markdown内容
            markdown_content = f"# {title}\n\n"
            if source:
                markdown_content += f"来源：{source}\n\n"
            
            # 使用集合来跟踪已处理的内容，避免重复
            processed_content = set()
            processed_content.add(title)  # 添加标题到已处理集合
            if source:
                processed_content.add(source)  # 添加来源到已处理集合
            
            # 获取所有内容元素
            elements = content_element.find_elements(By.CSS_SELECTOR, 'p, section, table, img')
            
            # 使用列表来保存处理后的内容
            content_blocks = []
            
            for elem in elements:
                # 处理图片
                if elem.tag_name == 'img':
                    try:
                        img_url = elem.get_attribute('data-src')
                        if img_url and img_url not in processed_content:
                            alt_text = elem.get_attribute('alt') or '图片'
                            content_blocks.append(f"![{alt_text}]({img_url})")
                            processed_content.add(img_url)
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
                            
                        # 生成表格内容的唯一标识
                        table_id = ''.join([row.text for row in rows])
                        if table_id in processed_content:
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
                        
                        content_blocks.append('\n'.join(table_content))
                        processed_content.add(table_id)
                        continue
                    except Exception as e:
                        self.logger.error(f"处理表格时出错: {str(e)}")
                        continue
                
                # 处理文本内容
                text = elem.text.strip()
                if not text or text in processed_content:
                    continue
                
                # 检查段落中的图片
                images = elem.find_elements(By.TAG_NAME, 'img')
                for img in images:
                    try:
                        img_url = img.get_attribute('data-src')
                        if img_url and img_url not in processed_content:
                            alt_text = img.get_attribute('alt') or '图片'
                            text += f"\n![{alt_text}]({img_url})"
                            processed_content.add(img_url)
                    except:
                        continue
                
                # 添加处理后的文本
                content_blocks.append(text)
                processed_content.add(text)
            
            # 合并内容块，每个块之间添加空行
            markdown_content += '\n\n'.join(content_blocks)
            
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

    def _scroll_and_extract_articles(self, driver) -> List[Dict[str, str]]:
        """滚动页面并提取文章信息"""
        articles = []
        scroll_count = 0
        last_articles_count = 0
        no_new_content_count = 0
        
        try:
            while True:
                scroll_count += 1
                self.logger.debug(f"执行第 {scroll_count} 次滚动")
                
                driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(3)
                
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li.album__list-item'))
                    )
                except Exception as e:
                    self.logger.warning(f"等待文章元素超时: {str(e)}")
                
                items = driver.find_elements(By.CSS_SELECTOR, 'li.album__list-item')
                self.logger.debug(f"当前页面找到 {len(items)} 个文章元素")
                
                for item in items:
                    try:
                        title = item.get_attribute('data-title')
                        link = item.get_attribute('data-link')
                        if title and link and {'title': title, 'url': link} not in articles:
                            articles.append({'title': title, 'url': link})
                            self.logger.debug(f"新增文章: {title}")
                    except Exception as e:
                        self.logger.error(f"提取文章信息时出错: {str(e)}")
                
                if len(articles) > last_articles_count:
                    self.logger.info(f"已找到 {len(articles)} 篇文章")
                    last_articles_count = len(articles)
                    no_new_content_count = 0
                else:
                    no_new_content_count += 1
                
                if no_new_content_count >= 3 or scroll_count > 100:
                    break
            
            return articles
        except Exception as e:
            self.logger.error(f"滚动和提取过程出错: {str(e)}")
            raise

    def _save_article_list(self, articles: List[Dict[str, str]]):
        """保存文章列表到文件"""
        try:
            # 保存为文本格式
            txt_file = os.path.join(self.output_dir, 'article_list.txt')
            self.logger.info(f"保存文本格式到: {txt_file}")
            with open(txt_file, 'w', encoding='utf-8') as f:
                for idx, article in enumerate(articles, 1):
                    f.write(f'[{idx}] 标题：{article["title"]}\n链接：{article["url"]}\n\n')
            
            # 保存为JSON格式
            json_file = os.path.join(self.output_dir, 'article_list.json')
            self.logger.info(f"保存JSON格式到: {json_file}")
            articles_json = [{'id': idx, **article} for idx, article in enumerate(articles, 1)]
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(articles_json, f, ensure_ascii=False, indent=2)
            
            self.logger.info("文章列表保存完成")
        except Exception as e:
            self.logger.error(f"保存文章列表时出错: {str(e)}")
            raise

    def _validate_url(self, url: str) -> bool:
        """验证URL是否为微信文章或合集URL"""
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            if 'mp.weixin.qq.com' not in parsed.netloc:
                return False
            return True
        except Exception as e:
            self.logger.error(f"URL验证失败: {str(e)}")
            return False

    def crawl_article(self, url: str, title: str = None):
        """爬取单篇文章"""
        driver = None
        try:
            # 准备文件名
            if title is None:
                title = url.split('/')[-1]
            safe_title = self._sanitize_filename(title)
            file_path = os.path.join(self.output_dir, f"{safe_title}.md")
            
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
                self.logger.info(f"✅ 文章保存成功: {safe_title}")
            else:
                self.logger.error(f"❌ 未能提取到文章内容: {title}")
            
        except Exception as e:
            self.logger.error(f"爬取文章时出错: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def crawl_article_set(self, url: str):
        """爬取文章合集"""
        driver = None
        try:
            self.logger.info("开始爬取文章合集...")
            self.logger.info(f"合集URL: {url}")
            
            # 设置浏览器驱动
            driver = self._setup_driver()
            
            # 访问页面
            driver.get(url)
            time.sleep(5)  # 等待页面加载
            
            # 提取文章列表
            articles = self._scroll_and_extract_articles(driver)
            
            if not articles:
                self.logger.error("未找到任何文章")
                return
            
            # 保存文章列表
            self._save_article_list(articles)
            
            # 爬取每篇文章
            total = len(articles)
            for idx, article in enumerate(articles, 1):
                self.logger.info(f"\n[{idx}/{total}] 开始处理文章...")
                self.crawl_article(article['url'], article['title'])
                time.sleep(3)  # 防止请求过于频繁
            
        except Exception as e:
            self.logger.error(f"爬取文章合集时出错: {str(e)}")
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def run(self):
        """运行爬虫"""
        print("\n=== 微信文章自动爬取工具 ===")
        print("1. 请输入要采集的链接（支持单篇文章或文章合集）")
        url = input("链接: ").strip()
        
        if not url:
            print("未输入URL，程序退出")
            return
            
        if not self._validate_url(url):
            print("无效的微信文章链接")
            return
            
        # 判断是否为合集链接
        if 'appmsgalbum' in url:
            self.crawl_article_set(url)
        else:
            self.crawl_article(url)
            
        print(f"\n✅ 爬取完成！文章已保存到目录: {self.output_dir}")

def main():
    """主函数"""
    try:
        # 获取输出目录
        print("\n=== 微信文章自动爬取工具 ===")
        print("请输入保存目录路径（直接回车将使用默认目录）：")
        output_dir = input().strip()
        
        # 如果没有输入，使用None让类使用默认命名
        if not output_dir:
            output_dir = None
            
        # 创建爬虫实例并运行
        crawler = AutoWxCrawler(output_dir)
        crawler.run()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == '__main__':
    main()
