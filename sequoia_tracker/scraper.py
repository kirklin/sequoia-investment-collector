import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import re
import os
import json
import signal
import sys
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sequoia-investment-collector")

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 全局变量，用于控制爬虫中断
SHOULD_STOP = False

# 检查点文件路径
CHECKPOINT_FILE = "scraper_checkpoint.json"
KNOWN_IDS_FILE = "known_company_ids.json"


def handle_interrupt(sig, frame):
    """处理中断信号（如Ctrl+C）"""
    global SHOULD_STOP
    logger.info("接收到中断信号，程序将在完成当前任务后退出...")
    SHOULD_STOP = True


def get_page(url, retries=3):
    """获取页面HTML内容"""
    for i in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"请求异常: {e}")
            if i < retries - 1:
                sleep_time = random.uniform(2, 5)
                logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                time.sleep(sleep_time)
            else:
                logger.error(f"重试 {retries} 次后仍然失败")
                return None


def download_image(url, company_name, company_id):
    """下载并保存公司logo图片"""
    if not url:
        return ""
    
    # 创建图片保存目录
    img_dir = "company_logos"
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    
    # 从URL中获取文件扩展名
    parsed_url = urlparse(url)
    file_ext = os.path.splitext(parsed_url.path)[1]
    if not file_ext:
        file_ext = ".png"  # 默认扩展名
    
    # 构建本地文件名，使用公司ID和名称
    img_filename = f"{company_id}_{company_name.replace(' ', '_')}{file_ext}"
    img_path = os.path.join(img_dir, img_filename)
    
    # 如果文件已存在，直接返回路径
    if os.path.exists(img_path):
        return img_path
    
    # 下载图片
    try:
        logger.info(f"正在下载公司 {company_name} 的logo: {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # 保存图片
        with open(img_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"已保存公司 {company_name} 的logo到 {img_path}")
        return img_path
    except Exception as e:
        logger.error(f"下载图片失败: {e}")
        return ""


def get_company_detail(company_id, nonce, company_name=""):
    """获取公司详细信息"""
    ajax_url = "https://www.hongshan.com/wp-admin/admin-ajax.php"
    payload = {
        "action": "load_company_content",
        "post_id": company_id,
    }
    
    # 如果有nonce，添加到请求中
    if nonce:
        payload["nonce"] = nonce
    
    try:
        response = requests.post(ajax_url, data=payload, headers=HEADERS, timeout=10)
        response.raise_for_status()
        detail_html = response.text
        
        # 检查响应是否包含实际内容，排除空响应或错误响应
        if not detail_html or len(detail_html.strip()) < 50 or "error" in detail_html.lower():
            return None
        
        detail_soup = BeautifulSoup(detail_html, "html.parser")
        
        # 解析公司信息
        company_data = {}
        
        # 提取官网URL
        website_link = detail_soup.find("a", class_="button--outline-light")
        if website_link and website_link.has_attr("href"):
            company_data["website_url"] = website_link["href"]
            if company_name:
                logger.info(f"成功获取到公司 {company_name} 的官网链接: {company_data['website_url']}")
        
        # 提取logo图片URL
        logo_img = detail_soup.find("img", class_="company__logo-image")
        if logo_img and logo_img.has_attr("src"):
            company_data["logo_url"] = logo_img["src"]
            
            # 下载并保存图片
            if company_name:
                img_path = download_image(company_data["logo_url"], company_name, company_id)
                company_data["logo_path"] = img_path
        
        # 提取完整描述
        desc_div = detail_soup.find("div", class_="wysiwyg--fs-lg")
        if desc_div:
            full_desc = desc_div.get_text(strip=True)
            if full_desc:
                company_data["full_description"] = full_desc
        
        # 检查是否有足够的数据说明这是一个有效的公司
        if company_data:
            return company_data
        return None
    
    except Exception as e:
        logger.error(f"获取公司详情失败: {e}")
        return None


def load_known_ids():
    """加载已知的公司ID"""
    if os.path.exists(KNOWN_IDS_FILE):
        try:
            with open(KNOWN_IDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"已加载 {len(data.get('valid_ids', []))} 个有效ID和 {len(data.get('invalid_ids', []))} 个无效ID")
                return data
        except Exception as e:
            logger.error(f"加载已知ID文件失败: {e}")
    
    # 如果文件不存在或读取失败，返回空数据
    return {"valid_ids": [], "invalid_ids": []}


def save_known_ids(valid_ids, invalid_ids):
    """保存已知的有效和无效公司ID"""
    try:
        data = {
            "valid_ids": list(valid_ids),
            "invalid_ids": list(invalid_ids),
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(KNOWN_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {len(valid_ids)} 个有效ID和 {len(invalid_ids)} 个无效ID")
        return True
    except Exception as e:
        logger.error(f"保存已知ID文件失败: {e}")
        return False


def save_checkpoint(last_id, companies):
    """保存爬取进度检查点"""
    try:
        data = {
            "last_id": last_id,
            "companies": companies,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存检查点，最后处理的ID: {last_id}，已爬取 {len(companies)} 家公司")
        return True
    except Exception as e:
        logger.error(f"保存检查点失败: {e}")
        return False


def load_checkpoint():
    """加载爬取进度检查点"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"已加载检查点，上次进度: ID {data.get('last_id')}，已爬取 {len(data.get('companies', []))} 家公司")
                return data
        except Exception as e:
            logger.error(f"加载检查点文件失败: {e}")
    
    # 如果文件不存在或读取失败，返回空数据
    return {"last_id": 0, "companies": []}


def scrape_hongshan(start_id=None, end_id=None, explore_additional=True, resume=False):
    """爬取红杉中国投资的公司
    
    参数:
        start_id: 开始搜索的ID，如果为None则从网页中提取
        end_id: 结束搜索的ID，如果为None则自动确定
        explore_additional: 是否探索额外ID
        resume: 是否从上次的检查点恢复
    """
    # 注册中断信号处理器
    signal.signal(signal.SIGINT, handle_interrupt)
    
    # 从检查点恢复
    if resume:
        checkpoint = load_checkpoint()
        if checkpoint and checkpoint.get("companies"):
            last_id = checkpoint.get("last_id", 0)
            companies = checkpoint.get("companies", [])
            logger.info(f"从检查点恢复，继续从ID {last_id} 开始爬取，已有 {len(companies)} 家公司数据")
            if start_id is None:
                start_id = last_id + 1
            return companies
    
    # 加载已知ID
    known_data = load_known_ids()
    valid_ids = set(known_data.get("valid_ids", []))
    invalid_ids = set(known_data.get("invalid_ids", []))
    
    url = "https://www.hongshan.com/companies/"
    logger.info(f"正在请求 {url}")
    
    html = get_page(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    companies = []
    company_ids = set()  # 用于跟踪已处理的公司ID
    
    # 查找公司表格
    table = soup.find("table", id="company_listing")
    if not table:
        logger.error("未找到公司列表表格")
        return []
    
    # 尝试从页面中获取nonce值，这在一些WordPress网站中是必需的
    nonce = ""
    script_tags = soup.find_all("script")
    for script in script_tags:
        if script.string and "nonce" in script.string:
            nonce_match = re.search(r'nonce["\']?\s*:\s*["\']([a-zA-Z0-9]+)["\']', script.string)
            if nonce_match:
                nonce = nonce_match.group(1)
                logger.info(f"找到nonce值: {nonce}")
                break
    
    # 解析表格行 - 只处理非child行（主要公司行）
    logger.info("正在爬取网页上显示的公司信息...")
    for row in table.find_all("tr"):
        # 检查是否被中断
        if SHOULD_STOP:
            logger.info("爬取过程被用户中断")
            break
            
        # 跳过表头和child行
        if row.get("class") and "child" in row.get("class"):
            continue
        if not row.find("td", class_="u-d-none"):  # 表头没有这个单元格
            continue
            
        try:
            # 提取公司ID - 在第一个td单元格中，class为u-d-none
            id_cell = row.find("td", class_="u-d-none")
            company_id = id_cell.get_text(strip=True) if id_cell else ""
            company_ids.add(company_id)  # 记录ID
            valid_ids.add(company_id)    # 添加到有效ID集合
            
            # 提取公司名称 - 在th单元格中，class包含company-listing__head
            name_cell = row.find("th", class_="company-listing__head")
            company_name = name_cell.get_text(strip=True) if name_cell else ""
            
            # 清理公司名称，去除前面的数字编号（如 "107 Saturnbird" -> "Saturnbird"）
            company_name = re.sub(r'^(\d+\s+)', '', company_name)
            
            # 提取公司简介 - 在td单元格中，class包含company-listing__text
            desc_cell = row.find("td", class_="company-listing__text")
            description = desc_cell.get_text(strip=True) if desc_cell else ""
            
            # 提取行业标签 - 在td单元格中，class包含company-listing__list
            industry_cell = row.find("td", class_="company-listing__list")
            industry = ""
            if industry_cell:
                industry_list = industry_cell.find_all("li")
                industry = ",".join([li.get_text(strip=True) for li in industry_list])
            
            # 使用AJAX接口获取公司详情和官网URL
            logger.info(f"正在获取公司 {company_name} (ID: {company_id}) 的详细信息")
            company_detail = get_company_detail(company_id, nonce, company_name)
            
            # 初始化公司数据
            company_data = {
                "id": company_id,
                "name": company_name,
                "description": description,
                "industry": industry,
                "url": "",
                "logo_url": "",
                "logo_path": ""
            }
            
            # 如果获取到详情，更新数据
            if company_detail:
                company_data["url"] = company_detail.get("website_url", "")
                company_data["logo_url"] = company_detail.get("logo_url", "")
                company_data["logo_path"] = company_detail.get("logo_path", "")
                # 如果有更完整的描述，更新描述
                if company_detail.get("full_description") and len(company_detail["full_description"]) > len(description):
                    company_data["description"] = company_detail["full_description"]
            
            # 如果没有获取到URL，使用备用URL
            if not company_data["url"]:
                company_data["url"] = f"https://www.hongshan.com/companies/?id={company_id}"
            
            companies.append(company_data)
            
            # 每爬取10家公司保存一次检查点
            if len(companies) % 10 == 0:
                save_checkpoint(int(company_id), companies)
        except Exception as e:
            logger.error(f"解析公司信息时发生错误: {e}")
    
    # 保存已知ID
    save_known_ids(valid_ids, invalid_ids)
    
    # 如果不需要探索额外ID，直接返回
    if not explore_additional:
        logger.info(f"从红杉中国网站抓取了 {len(companies)} 家公司，不探索额外ID")
        return companies
    
    # 确定ID的范围
    if start_id is None:
        id_min = 1
    else:
        id_min = int(start_id)
    
    if end_id is None:
        # 根据已知的ID范围调整搜索范围
        if company_ids:
            known_ids = [int(cid) for cid in company_ids if cid.isdigit()]
            if known_ids:
                id_min = max(1, min(known_ids) - 100) if start_id is None else id_min
                id_max = max(known_ids) + 100  # 向后搜索100个ID
        else:
            id_max = 3000  # 设置一个默认上限
    else:
        id_max = int(end_id)
    
    # 尝试通过ID范围查找额外的公司
    logger.info(f"正在尝试发现未在网页上显示的公司，搜索ID范围: {id_min} - {id_max}")
    print(f"将搜索 {id_max - id_min + 1} 个潜在ID...")
    
    # 尝试ID范围内的每个ID
    additional_count = 0
    tested_count = 0
    found_streak = 0  # 连续发现的计数
    not_found_streak = 0  # 连续未发现的计数
    
    try:
        for test_id in range(id_min, id_max + 1):
            # 检查是否被中断
            if SHOULD_STOP:
                logger.info("爬取过程被用户中断")
                break
                
            # 跳过已知的ID
            if str(test_id) in company_ids:
                continue
                
            # 跳过已知无效的ID
            if str(test_id) in invalid_ids:
                continue
                
            # 显示进度
            tested_count += 1
            if tested_count % 10 == 0:
                progress = (test_id - id_min) / (id_max - id_min) * 100
                print(f"进度: {progress:.1f}% [{test_id}/{id_max}] - 已发现 {additional_count} 家额外公司", end="\r")
                # 保存检查点
                save_checkpoint(test_id, companies)
            
            # 智能调整：如果连续50个ID都没有找到有效数据，可能进入了一个无效区域，跳过一部分
            if not_found_streak >= 50:
                jump_size = 50
                logger.info(f"连续 {not_found_streak} 个ID无效，跳过接下来的 {jump_size} 个ID")
                test_id += jump_size
                not_found_streak = 0
                continue
            
            # 间隔请求以避免过快
            time.sleep(random.uniform(0.3, 0.8))
            
            # 尝试获取公司详情
            company_detail = get_company_detail(str(test_id), nonce)
            
            # 如果获取到数据，添加到公司列表
            if company_detail:
                # 提取公司名称
                company_name = ""
                # 尝试从图片alt属性中获取名称
                if "logo_url" in company_detail:
                    img_url = company_detail["logo_url"]
                    img_soup = BeautifulSoup(f'<img src="{img_url}" alt="Company Name" />', "html.parser")
                    logo_img = img_soup.find("img")
                    if logo_img and logo_img.has_attr("alt") and logo_img["alt"] != "Company Name":
                        company_name = logo_img["alt"]
                        # 清理公司名称，去除前面的数字编号
                        company_name = re.sub(r'^(\d+\s+)', '', company_name)
                
                # 尝试从logo URL提取名称
                if not company_name and "logo_url" in company_detail:
                    logo_url = company_detail["logo_url"]
                    name_match = re.search(r'/([^/]+)\.[^.]+$', logo_url)
                    if name_match:
                        company_name = name_match.group(1).replace('-', ' ').title()
                        # 清理公司名称，去除前面的数字编号
                        company_name = re.sub(r'^(\d+\s+)', '', company_name)
                
                if not company_name:
                    company_name = f"未命名公司_{test_id}"
                
                logger.info(f"发现额外公司: {company_name} (ID: {test_id})")
                
                # 下载logo
                logo_path = ""
                if "logo_url" in company_detail:
                    logo_path = download_image(company_detail["logo_url"], company_name, str(test_id))
                
                # 创建公司数据
                company_data = {
                    "id": str(test_id),
                    "name": company_name,
                    "description": company_detail.get("full_description", ""),
                    "industry": "",  # 无法获取行业信息
                    "url": company_detail.get("website_url", ""),
                    "logo_url": company_detail.get("logo_url", ""),
                    "logo_path": logo_path
                }
                
                # 如果没有URL，使用备用URL
                if not company_data["url"]:
                    company_data["url"] = f"https://www.hongshan.com/companies/?id={test_id}"
                
                companies.append(company_data)
                additional_count += 1
                found_streak += 1
                not_found_streak = 0
                
                # 添加到已处理ID集合
                company_ids.add(str(test_id))
                valid_ids.add(str(test_id))
                
                # 每找到5家新公司保存一次检查点
                if additional_count % 5 == 0:
                    save_checkpoint(test_id, companies)
                    # 同时保存已知ID列表
                    save_known_ids(valid_ids, invalid_ids)
            else:
                # 添加到无效ID集合
                invalid_ids.add(str(test_id))
                found_streak = 0
                not_found_streak += 1
    except KeyboardInterrupt:
        logger.info("用户手动中断了搜索过程")
    finally:
        # 清除当前行
        print(" " * 100, end="\r")  
        # 保存最终检查点和已知ID
        save_checkpoint(id_max, companies)
        save_known_ids(valid_ids, invalid_ids)
    
    if additional_count > 0:
        logger.info(f"发现了 {additional_count} 家额外的公司信息")
    
    logger.info(f"从红杉中国网站共抓取了 {len(companies)} 家公司")
    return companies


def scrape_hsgcap():
    """爬取红杉全球投资的公司"""
    url = "https://www.hsgcap.com/companies/"
    logger.info(f"正在请求 {url}")
    
    html = get_page(url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, "html.parser")
    companies = []
    
    # 查找公司表格
    company_table = soup.find("table", id="company_listing")
    if not company_table:
        logger.error("未找到公司列表表格")
        return []
    
    # 查找所有parent行（主公司行）
    parent_rows = company_table.find_all("tr", class_=lambda c: c and "parent" in c)
    
    logger.info(f"找到 {len(parent_rows)} 个公司条目")
    
    for parent_row in parent_rows:
        try:
            # 提取公司ID - 在第一个td单元格中，class为u-d-none
            id_cell = parent_row.find("td", class_="u-d-none")
            company_id = id_cell.get_text(strip=True) if id_cell else ""
            
            # 提取公司名称 - 在th单元格中，class包含company-listing__head
            name_cell = parent_row.find("th", class_="company-listing__head")
            name = name_cell.get_text(strip=True) if name_cell else ""
            
            # 清理公司名称，去除前面的数字编号（如 "107 Saturnbird" -> "Saturnbird"）
            name = re.sub(r'^(\d+\s+)', '', name)
            
            # 提取公司简介 - 在td单元格中，class包含company-listing__text
            desc_cell = parent_row.find("td", class_="company-listing__text")
            description = desc_cell.get_text(strip=True) if desc_cell else ""
            
            # 提取行业标签 - 在td单元格中，class包含company-listing__list
            industry_cell = parent_row.find("td", class_="company-listing__list")
            industry = ""
            if industry_cell:
                industry_list = industry_cell.find_all("li")
                industry = ",".join([li.get_text(strip=True) for li in industry_list])
            
            # 查找对应的详情行和折叠区
            company_url = ""
            logo_url = ""
            full_description = description
            
            # 找到详情行
            target_id = parent_row.get("data-target")
            if target_id:
                # 尝试找到已展开的详情
                child_div = soup.find("div", id=target_id)
                if child_div:
                    # 提取logo URL
                    logo_img = child_div.find("img", class_="company__logo-image")
                    if logo_img and logo_img.has_attr("src"):
                        logo_url = logo_img["src"]
                    
                    # 提取完整描述
                    desc_div = child_div.find("div", class_="wysiwyg--fs-lg")
                    if desc_div:
                        full_desc = desc_div.get_text(strip=True)
                        if full_desc:
                            full_description = full_desc
                    
                    # 提取公司网站URL
                    website_link = child_div.find("a", class_="button--outline-light")
                    if website_link and website_link.has_attr("href"):
                        company_url = website_link["href"]
            
            # 如果我们没有获取到URL，使用HSG网站上的公司页面链接
            if not company_url:
                company_url = f"https://www.hsgcap.com/companies/?_categories={industry.lower()}"
            
            # 下载logo
            logo_path = ""
            if logo_url:
                logo_path = download_image(logo_url, name, company_id)
            
            companies.append({
                "id": company_id,
                "name": name,
                "description": full_description,
                "industry": industry,
                "url": company_url,
                "logo_url": logo_url,
                "logo_path": logo_path
            })
            
            # 间隔请求以避免过快
            time.sleep(random.uniform(0.2, 0.5))
            
        except Exception as e:
            logger.error(f"解析公司 {name if 'name' in locals() else '未知'} 信息时发生错误: {e}")
    
    logger.info(f"从红杉全球网站抓取了 {len(companies)} 家公司")
    return companies 
