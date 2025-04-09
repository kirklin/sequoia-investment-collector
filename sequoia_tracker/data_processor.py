import re
import logging
from datetime import datetime

logger = logging.getLogger("sequoia-investment-collector")


def clean_text(text):
    """清理文本内容，去除多余空白字符"""
    if not text:
        return ""
    # 去除多余空白字符
    text = re.sub(r'\s+', ' ', text)
    # 去除首尾空白
    return text.strip()


def extract_stage(description):
    """从描述中提取投资阶段信息"""
    stages = []
    stage_patterns = [
        (r'(种子轮|种子期|seed)', '种子轮'),
        (r'(天使轮|angel)', '天使轮'),
        (r'(pre-?A|PreA|Pre-?A)', 'Pre-A轮'),
        (r'(A\+?轮|A\+?[+]?[ ]?Round|Series A\+?)', 'A轮'),
        (r'(B\+?轮|B\+?[+]?[ ]?Round|Series B\+?)', 'B轮'),
        (r'(C\+?轮|C\+?[+]?[ ]?Round|Series C\+?)', 'C轮'),
        (r'(D\+?轮|D\+?[+]?[ ]?Round|Series D\+?)', 'D轮'),
        (r'(E\+?轮|E\+?[+]?[ ]?Round|Series E\+?)', 'E轮'),
        (r'(F\+?轮|F\+?[+]?[ ]?Round|Series F\+?)', 'F轮'),
        (r'(IPO|上市)', 'IPO/上市'),
    ]
    
    for pattern, stage in stage_patterns:
        if re.search(pattern, description, re.IGNORECASE):
            stages.append(stage)
    
    return ', '.join(stages) if stages else ''


def map_industry(industry):
    """标准化行业分类"""
    industry = clean_text(industry)
    
    industry_mapping = {
        # 中文行业映射
        '科技': '科技',
        '消费': '消费',
        '医疗': '医疗健康',
        '医疗健康': '医疗健康',
        '金融': '金融',
        '企业服务': '企业服务',
        '工业科技': '工业科技',
        '能源': '能源',
        '教育': '教育',
        
        # 英文行业映射
        'Technology': '科技',
        'Consumer': '消费',
        'Healthcare': '医疗健康',
        'Finance': '金融',
        'Enterprise': '企业服务',
        'Industrial': '工业科技',
        'Energy': '能源',
        'Education': '教育',
    }
    
    # 尝试直接匹配
    if industry in industry_mapping:
        return industry_mapping[industry]
    
    # 模糊匹配
    for key, value in industry_mapping.items():
        if key.lower() in industry.lower():
            return value
    
    return industry


def process_data(companies, source):
    """处理爬取的公司数据"""
    processed = []
    
    for company in companies:
        try:
            # 清理文本
            name = clean_text(company.get('name', ''))
            description = clean_text(company.get('description', ''))
            raw_industry = clean_text(company.get('industry', ''))
            
            # 标准化行业
            industry = map_industry(raw_industry)
            
            # 提取投资阶段
            investment_stage = extract_stage(description)
            
            # 创建处理后的记录
            processed_company = {
                'company_id': company.get('id', ''),
                'name': name,
                'description': description,
                'industry': industry,
                'investment_stage': investment_stage,
                'url': company.get('url', ''),
                'logo_url': company.get('logo_url', ''),
                'logo_path': company.get('logo_path', ''),
                'source': source,
                'crawl_date': datetime.now().strftime('%Y-%m-%d'),
            }
            
            processed.append(processed_company)
        except Exception as e:
            logger.error(f"处理公司 {company.get('name', '未知')} 数据时出错: {e}")
    
    return processed 
