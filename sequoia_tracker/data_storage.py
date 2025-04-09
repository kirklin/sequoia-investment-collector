import os
import pandas as pd
import logging

logger = logging.getLogger("sequoia-tracker")


def save_to_excel(df, output_path):
    """将数据保存到Excel文件"""
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 定义列顺序
        columns = [
            'company_id',
            'name',
            'description',
            'industry',
            'investment_stage',
            'source',
            'url',
            'crawl_date',
        ]
        
        # 重新排序列
        df = df.reindex(columns=columns)
        
        # 保存到Excel
        df.to_excel(output_path, index=False, engine='openpyxl')
        logger.info(f"数据已成功保存到 {output_path}")
        return True
    except Exception as e:
        logger.error(f"保存数据到Excel时出错: {e}")
        return False 
